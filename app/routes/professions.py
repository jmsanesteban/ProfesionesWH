import json
import os
import re
import unicodedata
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app, abort)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.profession import Profession, ProfessionSkill, ProfessionTalent, ProfessionTrapping
from app.models.skill import Skill
from app.models.talent import Talent
from app.utils import admin_required, require_permission

professions_bp = Blueprint('professions', __name__, template_folder='../templates')


@professions_bp.route('/')
def list_professions():
    type_filter = request.args.get('type', '')
    search = request.args.get('q', '').strip()
    query = Profession.query
    if type_filter in ('basic', 'advanced'):
        query = query.filter_by(type=type_filter)
    if search:
        query = query.filter(Profession.name.ilike(f'%{search}%'))
    professions = query.order_by(Profession.name).all()
    return render_template('professions/list.html', professions=professions,
                           type_filter=type_filter, search=search)


@professions_bp.route('/<int:prof_id>')
def detail(prof_id):
    prof = Profession.query.get_or_404(prof_id)
    return render_template('professions/detail.html', prof=prof)


@professions_bp.route('/nueva', methods=['GET', 'POST'])
@require_permission('professions.edit')
def create():
    skills = Skill.query.order_by(Skill.name_es).all()
    talents = Talent.query.order_by(Talent.name_es).all()

    if request.method == 'POST':
        prof = _profession_from_form(None)
        db.session.add(prof)
        db.session.flush()
        _save_skills_talents(prof)
        _save_trappings(prof)
        db.session.commit()
        flash(f'Profesión "{prof.name}" creada correctamente.', 'success')
        return redirect(url_for('professions.detail', prof_id=prof.id))

    all_profs = Profession.query.order_by(Profession.name).all()
    skill_specs = _load_skill_specs(skills)
    return render_template('professions/form.html', prof=None, skills=skills, talents=talents,
                           exits_list=all_profs, skill_specs=skill_specs)


@professions_bp.route('/<int:prof_id>/editar', methods=['GET', 'POST'])
@require_permission('professions.edit')
def edit(prof_id):
    prof = Profession.query.get_or_404(prof_id)
    skills = Skill.query.order_by(Skill.name_es).all()
    talents = Talent.query.order_by(Talent.name_es).all()

    if request.method == 'POST':
        _profession_from_form(prof)
        # Rebuild relationships
        ProfessionSkill.query.filter_by(profession_id=prof.id).delete()
        ProfessionTalent.query.filter_by(profession_id=prof.id).delete()
        ProfessionTrapping.query.filter_by(profession_id=prof.id).delete()
        db.session.flush()
        _save_skills_talents(prof)
        _save_trappings(prof)
        _cleanup_pending_in_description(prof)
        db.session.commit()
        flash(f'Profesión "{prof.name}" actualizada.', 'success')
        return redirect(url_for('professions.detail', prof_id=prof.id))

    all_profs = Profession.query.order_by(Profession.name).all()
    skill_specs = _load_skill_specs(skills)
    return render_template('professions/form.html', prof=prof, skills=skills, talents=talents,
                           exits_list=all_profs, skill_specs=skill_specs)


@professions_bp.route('/<int:prof_id>/eliminar', methods=['POST'])
@require_permission('professions.edit')
def delete(prof_id):
    prof = Profession.query.get_or_404(prof_id)
    name = prof.name
    db.session.delete(prof)
    db.session.commit()
    flash(f'Profesión "{name}" eliminada.', 'warning')
    return redirect(url_for('professions.list_professions'))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _profession_from_form(prof: Profession) -> Profession:
    """Create or update a Profession from POST form data."""
    f = request.form
    if prof is None:
        prof = Profession()
        prof.created_by_id = current_user.id

    prof.name = f.get('name', '').strip()
    prof.name_en = f.get('name_en', '').strip() or None
    prof.type = f.get('type', 'basic')
    prof.description = f.get('description', '').strip() or None

    # Primary characteristics
    for field in Profession.PRIMARY_FIELDS:
        val = f.get(field, '').strip()
        setattr(prof, field, int(val) if val else None)

    # Secondary characteristics
    for field in Profession.SECONDARY_FIELDS:
        val = f.get(field, '').strip()
        setattr(prof, field, int(val) if val else None)

    # Handle image upload
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'professions', filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            file.save(save_path)
            prof.image_path = os.path.join('professions', filename)

    return prof


def _save_skills_talents(prof: Profession):
    """Parse skill/talent selections from form and persist association rows."""
    form = request.form

    # Skills: 'skill_<id>' checkboxes (exclude 'skill_group_*' and 'skill_spec_*')
    skill_ids = [
        int(k[len('skill_'):])
        for k in form
        if k.startswith('skill_') and not k.startswith('skill_group_') and not k.startswith('skill_spec_')
    ]
    for skill_id in skill_ids:
        specs_raw = form.get(f'skill_spec_{skill_id}', '').strip()
        if specs_raw.startswith('['):
            # JSON format: spec skill — each entry carries its own group
            try:
                entries = json.loads(specs_raw)
            except Exception:
                entries = []
            for e in entries:
                spec = (e.get('spec') or '').strip() or None
                grp = e.get('group')
                entry_group = int(grp) if grp else None
                db.session.add(ProfessionSkill(
                    profession_id=prof.id, skill_id=skill_id,
                    specialization=spec, choice_group=entry_group,
                ))
        else:
            # Plain text: comma-separated specs with a shared group
            group_val = form.get(f'skill_group_{skill_id}', '').strip()
            choice_group = int(group_val) if group_val.isdigit() else None
            specs = [s.strip() for s in specs_raw.split(',') if s.strip()] if specs_raw else [None]
            for spec in specs:
                db.session.add(ProfessionSkill(
                    profession_id=prof.id, skill_id=skill_id,
                    specialization=spec, choice_group=choice_group,
                ))

    # Talents: 'talent_<id>' checkboxes (exclude 'talent_group_*' and 'talent_spec_*')
    talent_ids = [
        int(k[len('talent_'):])
        for k in form
        if k.startswith('talent_') and not k.startswith('talent_group_') and not k.startswith('talent_spec_')
    ]
    for talent_id in talent_ids:
        group_val = form.get(f'talent_group_{talent_id}', '').strip()
        choice_group = int(group_val) if group_val.isdigit() else None
        specs_raw = form.get(f'talent_spec_{talent_id}', '').strip()
        specs = [s.strip() for s in specs_raw.split(',') if s.strip()] if specs_raw else [None]
        for spec in specs:
            db.session.add(ProfessionTalent(
                profession_id=prof.id, talent_id=talent_id,
                specialization=spec, choice_group=choice_group,
            ))

    # Exits (career exits)
    exit_ids = request.form.getlist('exits')
    all_profs = {p.id: p for p in Profession.query.all()}
    prof.exits = [all_profs[int(eid)] for eid in exit_ids if int(eid) in all_profs and int(eid) != prof.id]


_PENDING_BLOCK_RE = re.compile(
    r'\n?\[(?P<tag>(?:SALIDAS|ACCESOS) PENDIENTES DE VINCULAR)\]:\s*(?P<list>[^\[]*)',
    re.IGNORECASE,
)


def _cleanup_pending_in_description(prof: Profession):
    """Remove linked exits/entries from the pending-link text in the description."""
    if not prof.description:
        return
    exit_names  = {e.name.lower() for e in prof.exits}
    entry_names = {e.name.lower() for e in prof.entries}

    def clean_block(m):
        tag   = m.group('tag').upper()
        items = [n.strip() for n in m.group('list').split(',') if n.strip()]
        linked = exit_names if 'SALIDAS' in tag else entry_names
        remaining = [n for n in items if n.lower() not in linked]
        return (f'\n[{tag}]: {", ".join(remaining)}') if remaining else ''

    desc = _PENDING_BLOCK_RE.sub(clean_block, prof.description).strip()
    prof.description = desc or None


def _load_skill_specs(skills) -> dict:
    """Return {skill_id: [{"nombre":…,"atributo":…,"descripcion":…}]} from data JSON."""
    data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'skill_specializations.json')
    try:
        with open(data_path, encoding='utf-8') as f:
            raw = json.load(f)
    except Exception:
        return {}

    def _norm(s: str) -> str:
        s = s.lower()
        s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        s = re.sub(r'\s*\([^)]*\)\s*$', '', s).strip()
        return s.rstrip('s')

    by_norm = {_norm(k): v for k, v in raw.items()}
    return {skill.id: by_norm[_norm(skill.name_es)]
            for skill in skills if _norm(skill.name_es) in by_norm}


def _save_trappings(prof: Profession):
    trappings_text = request.form.get('trappings', '')
    for line in trappings_text.split(','):
        name = line.strip()
        if name:
            db.session.add(ProfessionTrapping(profession_id=prof.id, name=name))
