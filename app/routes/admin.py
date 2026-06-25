import json
import logging
import os
import tempfile
import threading
import time
import uuid
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app, jsonify)
from flask_login import login_required
from app.extensions import db
from app.models.user import User
from app.models.profession import Profession, ProfessionSkill, ProfessionTalent, ProfessionTrapping
from app.models.skill import Skill
from app.models.talent import Talent
from app.utils import admin_required, allowed_file
from app.services.pdf_processor import process_pdf

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, template_folder='../templates')

# ---------------------------------------------------------------------------
# Async PDF job management (file-based state, cross-worker safe)
# ---------------------------------------------------------------------------

_JOBS_DIR = os.path.join(tempfile.gettempdir(), 'wh_pdf_jobs')
os.makedirs(_JOBS_DIR, exist_ok=True)


def _job_path(job_id: str) -> str:
    safe = ''.join(c for c in job_id if c.isalnum() or c == '-')
    return os.path.join(_JOBS_DIR, f'{safe}.json')


def _write_job(job_id: str, data: dict) -> None:
    path = _job_path(job_id)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def _read_job(job_id: str) -> dict | None:
    path = _job_path(job_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _run_pdf_job(job_id: str, file_bytes: bytes) -> None:
    def progress_cb(percent: int, stage: str) -> None:
        job = _read_job(job_id) or {}
        job.update(percent=percent, stage=stage)
        _write_job(job_id, job)

    try:
        result = process_pdf(file_bytes, progress_cb=progress_cb)
        job = _read_job(job_id) or {}
        job.update(percent=100, stage='Completado', done=True, result=result)
        _write_job(job_id, job)
    except Exception as e:
        logger.error('PDF job %s failed: %s', job_id, e, exc_info=True)
        job = _read_job(job_id) or {}
        job.update(done=True, error=str(e), stage='Error')
        _write_job(job_id, job)


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    stats = {
        'users': User.query.count(),
        'professions': Profession.query.count(),
        'skills': Skill.query.count(),
        'talents': Talent.query.count(),
        'basic': Profession.query.filter_by(type='basic').count(),
        'advanced': Profession.query.filter_by(type='advanced').count(),
    }
    return render_template('admin/dashboard.html', stats=stats)


# ---- User management ----

@admin_bp.route('/usuarios')
@login_required
@admin_required
def users():
    users_list = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users_list)


@admin_bp.route('/usuarios/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == request.environ.get('flask_login_user_id'):
        flash('No puedes desactivar tu propia cuenta.', 'danger')
    else:
        user.active = not user.active
        db.session.commit()
        status = 'activado' if user.active else 'desactivado'
        flash(f'Usuario "{user.username}" {status}.', 'info')
    return redirect(url_for('admin.users'))


@admin_bp.route('/usuarios/<int:user_id>/rol', methods=['POST'])
@login_required
@admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role', 'user')
    if new_role in ('admin', 'user'):
        user.role = new_role
        db.session.commit()
        flash(f'Rol de "{user.username}" cambiado a {new_role}.', 'info')
    return redirect(url_for('admin.users'))


@admin_bp.route('/usuarios/<int:user_id>/eliminar', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    from flask_login import current_user
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('No puedes eliminar tu propia cuenta.', 'danger')
    else:
        name = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuario "{name}" eliminado.', 'warning')
    return redirect(url_for('admin.users'))


# ---- PDF upload & review ----

@admin_bp.route('/pdf', methods=['GET', 'POST'])
@login_required
@admin_required
def pdf_upload():
    if request.method == 'GET':
        return render_template('admin/pdf_upload.html')

    # POST: validate file and start background job; return JSON
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No se seleccionó ningún archivo.'}), 400

    file = request.files['pdf_file']
    if not file or not file.filename:
        return jsonify({'error': 'Archivo vacío.'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Solo se aceptan archivos PDF.'}), 400

    file_bytes = file.read()
    job_id = str(uuid.uuid4())

    _write_job(job_id, {
        'id': job_id,
        'percent': 0,
        'stage': 'Iniciando procesamiento…',
        'done': False,
        'error': None,
        'result': None,
        'started_at': time.time(),
    })

    thread = threading.Thread(target=_run_pdf_job, args=(job_id, file_bytes), daemon=True)
    thread.start()

    return jsonify({'job_id': job_id})


@admin_bp.route('/pdf/progress/<job_id>')
@login_required
@admin_required
def pdf_progress(job_id):
    job = _read_job(job_id)
    if job is None:
        return jsonify({'error': 'Trabajo no encontrado.'}), 404
    return jsonify({
        'percent': job.get('percent', 0),
        'stage': job.get('stage', ''),
        'done': job.get('done', False),
        'error': job.get('error'),
    })


@admin_bp.route('/pdf/result/<job_id>')
@login_required
@admin_required
def pdf_result(job_id):
    job = _read_job(job_id)
    if job is None or not job.get('done'):
        flash('El procesamiento no ha terminado o el trabajo ha expirado.', 'danger')
        return redirect(url_for('admin.pdf_upload'))

    if job.get('error'):
        flash(f'Error durante el procesamiento: {job["error"]}', 'danger')
        return redirect(url_for('admin.pdf_upload'))

    result = job.get('result') or {}

    try:
        os.remove(_job_path(job_id))
    except OSError:
        pass

    for err in result.get('errors', []):
        flash(err, 'danger')

    all_skills   = Skill.query.order_by(Skill.name_es).all()
    all_talents  = Talent.query.order_by(Talent.name_es).all()
    skills_data  = [{'es': s.name_es, 'en': s.name_en or ''} for s in all_skills]
    talents_data = [{'es': t.name_es, 'en': t.name_en or ''} for t in all_talents]

    professions = _validate_pdf_professions(result.get('professions', []), all_skills, all_talents)

    return render_template(
        'admin/pdf_review.html',
        pages=result.get('pages', []),
        professions=professions,
        skills_data=skills_data,
        talents_data=talents_data,
        db_empty=len(all_skills) == 0 and len(all_talents) == 0,
    )


@admin_bp.route('/pdf/guardar', methods=['POST'])
@login_required
@admin_required
def pdf_save():
    """Save one parsed profession from the PDF review form."""
    from flask_login import current_user

    name = request.form.get('name', '').strip()
    if not name:
        flash('La profesión necesita un nombre.', 'danger')
        return redirect(url_for('admin.pdf_upload'))

    prof = Profession(
        name=name,
        name_en=request.form.get('name_en', '').strip() or None,
        type=request.form.get('type', 'basic'),
        description=request.form.get('description', '').strip() or None,
        created_by_id=current_user.id,
    )

    for field in Profession.PRIMARY_FIELDS + Profession.SECONDARY_FIELDS:
        val = request.form.get(field, '').strip()
        setattr(prof, field, int(val) if val.lstrip('-').isdigit() else None)

    db.session.add(prof)
    db.session.flush()

    # Trappings
    for item in request.form.get('trappings_raw', '').split(','):
        item = item.strip()
        if item:
            db.session.add(ProfessionTrapping(profession_id=prof.id, name=item))

    # Skills: match by name (best-effort fuzzy)
    _match_and_save_skills(prof, request.form.get('skills_raw', ''))
    _match_and_save_talents(prof, request.form.get('talents_raw', ''))

    # Career exits (just store raw names for now; admin can link later)
    # We store them in description as a note if prof doesn't exist yet
    exits_raw = request.form.get('exits_raw', '').strip()
    entries_raw = request.form.get('entries_raw', '').strip()
    if exits_raw or entries_raw:
        note = ''
        if exits_raw:
            note += f'\n[SALIDAS PENDIENTES DE VINCULAR]: {exits_raw}'
        if entries_raw:
            note += f'\n[ACCESOS PENDIENTES DE VINCULAR]: {entries_raw}'
        prof.description = (prof.description or '') + note

    db.session.commit()
    flash(f'Profesión "{prof.name}" guardada. Recuerda vincular accesos/salidas.', 'success')
    return redirect(url_for('professions.edit', prof_id=prof.id))


def _validate_pdf_professions(professions: list, all_skills, all_talents) -> list:
    """
    For each profession dict, add:
      unmatched_skills  — items from skills_raw that couldn't be matched to any DB skill
      unmatched_talents — items from talents_raw that couldn't be matched to any DB talent
      no_exits          — True if exits_raw is empty
      no_entries        — True if entries_raw is empty
    """
    import difflib

    skill_names  = set()
    for s in all_skills:
        skill_names.add(s.name_es.lower())
        if s.name_en:
            skill_names.add(s.name_en.lower())

    talent_names = set()
    for t in all_talents:
        talent_names.add(t.name_es.lower())
        if t.name_en:
            talent_names.add(t.name_en.lower())

    for prof in professions:
        unmatched_skills = []
        if skill_names:
            for raw in prof.get('skills_raw', '').replace(' o ', ',').replace(' or ', ',').split(','):
                item = raw.strip()
                if not item:
                    continue
                if not difflib.get_close_matches(item.lower(), skill_names, n=1, cutoff=0.65):
                    unmatched_skills.append(item)

        unmatched_talents = []
        if talent_names:
            for raw in prof.get('talents_raw', '').replace(' o ', ',').replace(' or ', ',').split(','):
                item = raw.strip()
                if not item:
                    continue
                if not difflib.get_close_matches(item.lower(), talent_names, n=1, cutoff=0.65):
                    unmatched_talents.append(item)

        prof['unmatched_skills']  = unmatched_skills
        prof['unmatched_talents'] = unmatched_talents
        prof['no_exits']    = not prof.get('exits_raw', '').strip()
        prof['no_entries']  = not prof.get('entries_raw', '').strip()

    return professions


def _match_and_save_skills(prof, skills_raw: str):
    import difflib
    all_skills = Skill.query.all()
    skill_map = {s.name_es.lower(): s for s in all_skills}
    skill_map.update({s.name_en.lower(): s for s in all_skills if s.name_en})

    # Split on commas and 'o'/'or'
    parts = [p.strip() for p in skills_raw.replace(' o ', ',').replace(' or ', ',').split(',')]
    group = None
    for raw_part in parts:
        if not raw_part:
            continue
        matches = difflib.get_close_matches(raw_part.lower(), skill_map.keys(), n=1, cutoff=0.7)
        if matches:
            skill = skill_map[matches[0]]
            ps = ProfessionSkill(profession_id=prof.id, skill_id=skill.id, choice_group=group)
            db.session.add(ps)


def _match_and_save_talents(prof, talents_raw: str):
    import difflib
    all_talents = Talent.query.all()
    talent_map = {t.name_es.lower(): t for t in all_talents}
    talent_map.update({t.name_en.lower(): t for t in all_talents if t.name_en})

    parts = [p.strip() for p in talents_raw.replace(' o ', ',').replace(' or ', ',').split(',')]
    group = None
    for raw_part in parts:
        if not raw_part:
            continue
        matches = difflib.get_close_matches(raw_part.lower(), talent_map.keys(), n=1, cutoff=0.7)
        if matches:
            talent = talent_map[matches[0]]
            pt = ProfessionTalent(profession_id=prof.id, talent_id=talent.id, choice_group=group)
            db.session.add(pt)
