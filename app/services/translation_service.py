import logging

logger = logging.getLogger(__name__)

try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False

_CHUNK_SIZE = 4500  # GoogleTranslator has a ~5000 char limit per call


def detect_language(text: str) -> str:
    """Returns ISO 639-1 language code or 'unknown'."""
    if not LANGDETECT_AVAILABLE or not text:
        return 'unknown'
    try:
        return detect(text[:500])
    except Exception:
        return 'unknown'


def translate_to_spanish(text: str) -> str:
    """Translate text to Spanish. Returns original text if translation fails."""
    if not text or not TRANSLATOR_AVAILABLE:
        return text

    lang = detect_language(text)
    if lang in ('es', 'unknown'):
        return text

    try:
        translator = GoogleTranslator(source='auto', target='es')
        if len(text) <= _CHUNK_SIZE:
            return translator.translate(text) or text

        # Split into chunks preserving newlines
        lines = text.split('\n')
        translated_lines = []
        chunk = ''
        for line in lines:
            if len(chunk) + len(line) + 1 > _CHUNK_SIZE:
                if chunk:
                    translated_lines.append(translator.translate(chunk) or chunk)
                chunk = line + '\n'
            else:
                chunk += line + '\n'
        if chunk:
            translated_lines.append(translator.translate(chunk) or chunk)

        return '\n'.join(translated_lines)
    except Exception as e:
        logger.warning(f"Translation failed: {e}")
        return text


def needs_translation(text: str) -> bool:
    lang = detect_language(text)
    return lang not in ('es', 'unknown', '')


def force_translate_to_spanish(text: str) -> str:
    """Translate to Spanish bypassing language detection (use when source is known non-Spanish)."""
    if not text or not TRANSLATOR_AVAILABLE:
        return text
    try:
        translator = GoogleTranslator(source='auto', target='es')
        return translator.translate(text) or text
    except Exception as e:
        logger.warning(f"Force translation failed: {e}")
        return text
