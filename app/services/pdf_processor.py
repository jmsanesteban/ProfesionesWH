"""
PDF processing service.

Architecture (per page):
  1. Extract text (digital) or OCR (scanned) → for sections and translation.
  2. Extract word-level positions → detect and parse the stat table by row alignment,
     bypassing the flat-text problem that loses table structure.
  3. Extract labeled sections (Skills, Talents, Trappings, Entries, Exits) from text.
  4. Translate to Spanish if needed.
  5. Emit one profession entry per page that looks like a career page
     (has stats AND at least one content section).
"""

import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available – PDF text extraction disabled.")

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not available – OCR fallback disabled.")

try:
    import pytesseract
    from PIL import Image  # noqa: F401
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract / Pillow not available – OCR disabled.")

from app.services.translation_service import (
    translate_to_spanish, needs_translation, force_translate_to_spanish
)

_MIN_TEXT_LENGTH = 50  # chars per page below which we assume it is a scan


# ---------------------------------------------------------------------------
# Stat table mappings
# ---------------------------------------------------------------------------

_PRIMARY_MAP = {
    'HA': 'ws',  'WS': 'ws',
    'HP': 'bs',  'BS': 'bs',
    'F':  's_char', 'S': 's_char',
    'R':  't_char', 'T': 't_char',
    'AG': 'ag',
    'I':  'int_char', 'INT': 'int_char',
    'V':  'wp',  'WP': 'wp',
    'EM': 'fel', 'FEL': 'fel',
}

_SECONDARY_MAP = {
    'A':   'attacks',
    'H':   'wounds',   'W':   'wounds',
    'BF':  'strength_bonus',  'SB':  'strength_bonus',
    'BR':  'toughness_bonus', 'TB':  'toughness_bonus',
    'M':   'movement',
    'MAG': 'magic',
    'PL':  'insanity_points', 'IP':  'insanity_points',
    'PD':  'fate_points',     'FP':  'fate_points',
}

_ALL_STAT_KEYS = frozenset(_PRIMARY_MAP) | frozenset(_SECONDARY_MAP)

_RE_VALUE   = re.compile(r'[+\-]?\s*\d+')
_RE_DASH    = re.compile(r'^[-—–]+$')

# ---------------------------------------------------------------------------
# Section regexes
# ---------------------------------------------------------------------------

_RE_SECTION = {
    'skills':    re.compile(r'^(?:habilidades?|sk\w+s?)\s*:', re.IGNORECASE | re.MULTILINE),
    'talents':   re.compile(r'^(?:talentos?|talents?)\s*:', re.IGNORECASE | re.MULTILINE),
    'trappings': re.compile(r'^(?:enseres?|trappings?)\s*:', re.IGNORECASE | re.MULTILINE),
    'entries':   re.compile(r'^(?:accesos?|entradas?|career\s+entr(?:y|ies))\s*:', re.IGNORECASE | re.MULTILINE),
    'exits':     re.compile(r'^(?:salidas?|career\s+exits?)\s*:', re.IGNORECASE | re.MULTILINE),
}
_SECTION_ORDER = ['skills', 'talents', 'trappings', 'entries', 'exits']

# Junk at the start of OCR-extracted name lines: page numbers, decorations
_RE_LEADING_JUNK = re.compile(r'^[\d.\s\-–—♦•★◆▶▸·]+')

# OCR often splits a capital letter from the rest of its word: "A Nimal" → "Animal"
_RE_SPLIT_LETTER = re.compile(r'\b([A-Z])\s+([A-Z][a-z]{2,})')


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def process_pdf(file_bytes: bytes, progress_cb=None) -> dict:
    """
    Process a PDF binary.  Returns:
      {
        'pages':       [{'page': int, 'text': str, 'translated': bool}, ...],
        'professions': [profession_dict, ...],
        'errors':      [str, ...],
      }
    progress_cb(percent, stage) is called after each page when provided.
    """
    result = {'pages': [], 'professions': [], 'errors': []}

    if not PYMUPDF_AVAILABLE:
        result['errors'].append("PyMuPDF no está disponible. Instala las dependencias correctamente.")
        return result

    try:
        doc = fitz.open(stream=file_bytes, filetype='pdf')
    except Exception as e:
        result['errors'].append(f"Error al abrir el PDF: {e}")
        return result

    total_pages = len(doc)

    for page_num in range(total_pages):
        page     = doc[page_num]
        raw_text = page.get_text("text").strip()
        is_scan  = len(raw_text) < _MIN_TEXT_LENGTH

        # ---- 1. Text + word-row extraction ----
        if is_scan:
            if progress_cb:
                progress_cb(
                    5 + int(page_num / total_pages * 75),
                    f'OCR página {page_num + 1} de {total_pages}…'
                )
            text, word_rows = _ocr_page(file_bytes, page_num)
        else:
            if progress_cb:
                progress_cb(
                    5 + int(page_num / total_pages * 75),
                    f'Extrayendo página {page_num + 1} de {total_pages}…'
                )
            text      = raw_text
            word_rows = _digital_word_rows(page)

        # ---- 2. Translation ----
        if needs_translation(text):
            if progress_cb:
                progress_cb(
                    5 + int(page_num / total_pages * 75),
                    f'Traduciendo página {page_num + 1} de {total_pages}…'
                )
            text           = translate_to_spanish(text)
            was_translated = True
        else:
            was_translated = False

        result['pages'].append({
            'page':       page_num + 1,
            'text':       text,
            'translated': was_translated,
        })

        # ---- 3. Stat extraction (positional) ----
        stats = _extract_stats(word_rows)

        # ---- 4. Section extraction (text-based) ----
        sections = _parse_sections(text)

        # ---- 5. Emit profession entry if this is a career page ----
        if _is_career_page(stats, sections):
            prof_type = (
                'advanced'
                if re.search(r'\bavan[cz]ad[ao]\b|\badvanced\b', text, re.IGNORECASE)
                else 'basic'
            )
            raw_name = _fix_ocr_name(_extract_name(page, text, is_scan))
            if was_translated and raw_name:
                # Page was in English: store English original + translate for Spanish
                name_en = raw_name
                name_es = force_translate_to_spanish(raw_name) or raw_name
            else:
                name_es = raw_name
                name_en = ''

            result['professions'].append({
                'name':        name_es,
                'name_en':     name_en,
                'type':        prof_type,
                'description': '',
                **_empty_stats(),
                **stats,
                **sections,
            })

        if progress_cb:
            progress_cb(
                5 + int((page_num + 1) / total_pages * 75),
                f'Procesada página {page_num + 1} de {total_pages}'
            )

    doc.close()
    return result


# ---------------------------------------------------------------------------
# Text / OCR extraction
# ---------------------------------------------------------------------------

def _ocr_page(file_bytes: bytes, page_index: int):
    """Return (text, sorted_word_rows) via a single Tesseract call."""
    if not PDF2IMAGE_AVAILABLE or not TESSERACT_AVAILABLE:
        return '', []
    try:
        images = convert_from_bytes(
            file_bytes, first_page=page_index + 1, last_page=page_index + 1, dpi=300
        )
        if not images:
            return '', []

        from pytesseract import Output
        data = pytesseract.image_to_data(
            images[0], lang='spa+eng', output_type=Output.DICT
        )

        rows_dict  = defaultdict(list)
        text_lines = defaultdict(list)

        for i in range(len(data['text'])):
            word = data['text'][i].strip()
            conf_raw = str(data['conf'][i])
            conf = int(conf_raw) if conf_raw.lstrip('-').isdigit() else -1
            if not word or conf < 20:
                continue
            line_key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
            text_lines[line_key].append(word)
            y_center = data['top'][i] + data['height'][i] // 2
            rows_dict[round(y_center / 15) * 15].append((data['left'][i], word))

        text = '\n'.join(' '.join(text_lines[k]) for k in sorted(text_lines))
        sorted_rows = [
            [w for _, w in sorted(rows_dict[k])]
            for k in sorted(rows_dict)
        ]
        return text, sorted_rows

    except Exception as e:
        logger.warning("OCR failed on page %d: %s", page_index + 1, e)
        return '', []


def _digital_word_rows(page) -> list:
    """Extract word positions from a digital PDF page using PyMuPDF."""
    try:
        words = page.get_text("words")
        # words: (x0, y0, x1, y1, word, block, line, word_idx)
        rows_dict = defaultdict(list)
        for w in words:
            x0, y0, x1, y1, word = w[:5]
            word = word.strip()
            if not word:
                continue
            y_center = (y0 + y1) / 2
            rows_dict[round(y_center / 8) * 8].append((x0, word))
        return [
            [w for _, w in sorted(rows_dict[k])]
            for k in sorted(rows_dict)
        ]
    except Exception as e:
        logger.warning("Word extraction failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Stat extraction (positional)
# ---------------------------------------------------------------------------

def _parse_value(token: str):
    """Parse '+25%', '—', '-', '+6' → int or None."""
    token = token.strip()
    if _RE_DASH.match(token) or token == '':
        return None
    m = _RE_VALUE.search(token)
    return int(m.group().replace(' ', '')) if m else None


def _parse_row_pair(header_row: list, value_row: list, mapping: dict) -> dict:
    """Map header[i] → field, value[i] → int, using direct index alignment."""
    result = {}
    for i, header in enumerate(header_row):
        field = mapping.get(header.upper())
        if field and i < len(value_row):
            result[field] = _parse_value(value_row[i])
    return result


def _extract_stats(sorted_rows: list) -> dict:
    """
    Scan word rows for a stat header line (≥3 known abbreviations that make up
    ≥60% of the line's words) then read values from the very next row.
    Works identically for digital-PDF and OCR word rows.
    """
    primary_result   = {}
    secondary_result = {}

    for i, row in enumerate(sorted_rows):
        if i + 1 >= len(sorted_rows) or not row:
            continue

        upper = [w.upper() for w in row]
        n     = len(upper)
        stat_frac    = sum(1 for w in upper if w in _ALL_STAT_KEYS) / n
        primary_hits = sum(1 for w in upper if w in _PRIMARY_MAP)
        sec_hits     = sum(1 for w in upper if w in _SECONDARY_MAP)

        next_row = sorted_rows[i + 1]

        if primary_hits >= 3 and stat_frac >= 0.6 and not primary_result:
            parsed = _parse_row_pair(row, next_row, _PRIMARY_MAP)
            if any(v is not None for v in parsed.values()):
                primary_result = parsed

        if sec_hits >= 3 and stat_frac >= 0.6 and not secondary_result:
            parsed = _parse_row_pair(row, next_row, _SECONDARY_MAP)
            if any(v is not None for v in parsed.values()):
                secondary_result = parsed

    return {**primary_result, **secondary_result}


def _empty_stats() -> dict:
    return {
        'ws': None, 'bs': None, 's_char': None, 't_char': None,
        'ag': None, 'int_char': None, 'wp': None, 'fel': None,
        'attacks': None, 'wounds': None, 'strength_bonus': None,
        'toughness_bonus': None, 'movement': None, 'magic': None,
        'insanity_points': None, 'fate_points': None,
    }


# ---------------------------------------------------------------------------
# Section extraction (text-based — already works well)
# ---------------------------------------------------------------------------

def _parse_sections(text: str) -> dict:
    """Extract Skills, Talents, Trappings, Entries, Exits from page text."""
    sections = {k + '_raw': '' for k in _SECTION_ORDER}
    for idx, key in enumerate(_SECTION_ORDER):
        m = _RE_SECTION[key].search(text)
        if not m:
            continue
        end = len(text)
        for later in _SECTION_ORDER[idx + 1:]:
            nm = _RE_SECTION[later].search(text, m.end())
            if nm and nm.start() < end:
                end = nm.start()
        sections[key + '_raw'] = text[m.end():end].strip().strip(':').strip()
    return sections


# ---------------------------------------------------------------------------
# Career page detection & name extraction
# ---------------------------------------------------------------------------

def _is_career_page(stats: dict, sections: dict) -> bool:
    """
    Only emit a profession entry when the page has BOTH positional stats AND
    at least one meaningful content section.  This prevents career-summary
    tables (stats but no sections) and lore pages (sections but no stats)
    from generating false entries.
    """
    has_stats = any(v is not None for v in stats.values())
    has_sections = (
        len(sections.get('skills_raw', '').strip()) > 10
        or len(sections.get('talents_raw', '').strip()) > 10
        or len(sections.get('trappings_raw', '').strip()) > 5
    )
    return has_stats and has_sections


def _fix_ocr_name(name: str) -> str:
    """
    Repair OCR-split capital letters: 'A Nimal T Rainer' → 'Animal Trainer'.
    Applied iteratively until stable, then collapses extra spaces.
    """
    prev = None
    while prev != name:
        prev = name
        name = _RE_SPLIT_LETTER.sub(
            lambda m: m.group(1) + m.group(2)[0].lower() + m.group(2)[1:],
            name,
        )
    return re.sub(r'\s{2,}', ' ', name).strip()


def _extract_name(page, text: str, is_scan: bool) -> str:
    """
    For digital PDFs: return the text of the span with the largest font size.
    Fallback for all pages: first ALL-CAPS line with ≥3 real letters.
    """
    if not is_scan:
        try:
            page_dict = page.get_text("dict")
            max_size  = 0
            candidate = ''
            for block in page_dict.get('blocks', []):
                if block.get('type') != 0:
                    continue
                for line in block.get('lines', []):
                    for span in line.get('spans', []):
                        size      = span.get('size', 0)
                        span_text = span.get('text', '').strip()
                        if size > max_size and sum(1 for c in span_text if c.isalpha()) >= 2:
                            max_size  = size
                            candidate = ' '.join(
                                s.get('text', '') for s in line.get('spans', [])
                            ).strip()
            if candidate and sum(1 for c in candidate if c.isalpha()) >= 2:
                return candidate.title()
        except Exception:
            pass

    # Fallback: first ALL-CAPS line of reasonable length
    for line in text.split('\n'):
        cleaned = _RE_LEADING_JUNK.sub('', line.strip()).strip()
        if (cleaned
                and cleaned == cleaned.upper()
                and sum(1 for c in cleaned if c.isalpha()) >= 3
                and len(cleaned.split()) <= 6):
            return cleaned.title()

    return ''


# ---------------------------------------------------------------------------
# Kept for backwards compatibility (no longer called by process_pdf)
# ---------------------------------------------------------------------------

def parse_professions(text: str) -> list:
    return []
