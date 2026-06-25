import os
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, Response)
from flask_login import login_required
from app.extensions import db
from app.models.skill import Skill
from app.models.talent import Talent
from app.models.profession import Profession, ProfessionSkill, ProfessionTalent
from app.utils import admin_required

skills_talents_bp = Blueprint('skills_talents', __name__, template_folder='../templates')


# ─────────────────────────────────────────────────────────────────────────────
# Skills — CRUD
# ─────────────────────────────────────────────────────────────────────────────

@skills_talents_bp.route('/habilidades')
def list_skills():
    search     = request.args.get('q', '').strip()
    search_all = request.args.get('search_all', '0') == '1'
    tipo       = request.args.get('tipo', '')        # 'basic' | 'advanced' | ''
    caract     = request.args.get('caract', '').strip()

    query = Skill.query

    if search:
        if search_all:
            query = query.filter(
                Skill.name_es.ilike(f'%{search}%')
                | Skill.name_en.ilike(f'%{search}%')
                | Skill.description.ilike(f'%{search}%')
                | Skill.caracteristicas.ilike(f'%{search}%')
                | Skill.talentos_asociados.ilike(f'%{search}%')
            )
        else:
            query = query.filter(
                Skill.name_es.ilike(f'%{search}%') | Skill.name_en.ilike(f'%{search}%')
            )

    if tipo == 'basic':
        query = query.filter(Skill.is_advanced == False)
    elif tipo == 'advanced':
        query = query.filter(Skill.is_advanced == True)

    if caract:
        query = query.filter(Skill.caracteristicas.ilike(f'%{caract}%'))

    skills = query.order_by(Skill.name_es).all()

    # Unique characteristic values for the filter dropdown
    rows = db.session.query(Skill.caracteristicas).filter(Skill.caracteristicas.isnot(None)).all()
    all_caracts = sorted({
        c.strip()
        for (raw,) in rows
        for c in raw.split(',')
        if c.strip()
    })

    return render_template(
        'skills/list.html',
        skills=skills, search=search, search_all=search_all,
        tipo=tipo, caract=caract, all_caracts=all_caracts,
    )


@skills_talents_bp.route('/habilidades/<int:skill_id>')
def skill_detail(skill_id):
    skill    = Skill.query.get_or_404(skill_id)
    prof_ids = [ps.profession_id for ps in ProfessionSkill.query.filter_by(skill_id=skill_id).all()]
    professions = Profession.query.filter(Profession.id.in_(prof_ids)).order_by(Profession.name).all()
    return render_template('skills/detail.html', skill=skill, professions=professions)


@skills_talents_bp.route('/habilidades/nueva', methods=['GET', 'POST'])
@login_required
@admin_required
def create_skill():
    if request.method == 'POST':
        skill = Skill(
            name_es=request.form.get('name_es', '').strip(),
            name_en=request.form.get('name_en', '').strip() or None,
            description=request.form.get('description', '').strip() or None,
            is_advanced=bool(request.form.get('is_advanced')),
            caracteristicas=request.form.get('caracteristicas', '').strip() or None,
            talentos_asociados=request.form.get('talentos_asociados', '').strip() or None,
        )
        db.session.add(skill)
        db.session.commit()
        flash(f'Habilidad "{skill.name_es}" creada.', 'success')
        return redirect(url_for('skills_talents.list_skills'))
    return render_template('skills/form.html', skill=None)


@skills_talents_bp.route('/habilidades/<int:skill_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_skill(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    if request.method == 'POST':
        skill.name_es            = request.form.get('name_es', '').strip()
        skill.name_en            = request.form.get('name_en', '').strip() or None
        skill.description        = request.form.get('description', '').strip() or None
        skill.is_advanced        = bool(request.form.get('is_advanced'))
        skill.caracteristicas    = request.form.get('caracteristicas', '').strip() or None
        skill.talentos_asociados = request.form.get('talentos_asociados', '').strip() or None
        db.session.commit()
        flash(f'Habilidad "{skill.name_es}" actualizada.', 'success')
        return redirect(url_for('skills_talents.list_skills'))
    return render_template('skills/form.html', skill=skill)


@skills_talents_bp.route('/habilidades/<int:skill_id>/eliminar', methods=['POST'])
@login_required
@admin_required
def delete_skill(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    name  = skill.name_es
    db.session.delete(skill)
    db.session.commit()
    flash(f'Habilidad "{name}" eliminada.', 'warning')
    return redirect(url_for('skills_talents.list_skills'))


# ─────────────────────────────────────────────────────────────────────────────
# Skills — Import / Export
# ─────────────────────────────────────────────────────────────────────────────

@skills_talents_bp.route('/habilidades/importar', methods=['GET', 'POST'])
@login_required
@admin_required
def import_skills():
    if request.method == 'GET':
        return render_template('skills/import.html')

    f = request.files.get('file')
    if not f or not f.filename:
        flash('Selecciona un fichero.', 'danger')
        return redirect(request.url)

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ('.txt', '.csv', '.xlsx', '.xls'):
        flash('Formato no soportado. Usa .txt, .csv o .xlsx.', 'danger')
        return redirect(request.url)

    from app.services.import_service import parse_skills
    try:
        entries = parse_skills(f.read(), ext)
    except Exception as e:
        flash(f'Error al leer el fichero: {e}', 'danger')
        return redirect(request.url)

    existing = {s.name_es.lower(): s for s in Skill.query.all()}
    created = updated = skipped = 0
    mode = request.form.get('mode', 'skip')

    for entry in entries:
        name_lower = entry.get('name_es', '').lower()
        if not name_lower:
            continue
        if name_lower in existing:
            if mode == 'update':
                s = existing[name_lower]
                for field in ('description', 'is_advanced', 'caracteristicas', 'talentos_asociados'):
                    if field in entry and entry[field] is not None:
                        setattr(s, field, entry[field])
                updated += 1
            else:
                skipped += 1
        else:
            s = Skill(
                name_es=entry['name_es'],
                description=entry.get('description'),
                is_advanced=entry.get('is_advanced', False),
                caracteristicas=entry.get('caracteristicas'),
                talentos_asociados=entry.get('talentos_asociados'),
            )
            db.session.add(s)
            created += 1

    db.session.commit()
    flash(f'Importación completada: {created} creadas, {updated} actualizadas, {skipped} omitidas.', 'success')
    return redirect(url_for('skills_talents.list_skills'))


@skills_talents_bp.route('/habilidades/exportar')
@login_required
@admin_required
def export_skills():
    fmt    = request.args.get('f', 'txt').lower()
    skills = Skill.query.order_by(Skill.name_es).all()
    from app.services.import_service import export_skills_text, export_skills_csv, export_skills_xlsx

    if fmt == 'csv':
        data = export_skills_csv(skills)
        return Response(data, mimetype='text/csv; charset=utf-8-sig',
                        headers={'Content-Disposition': 'attachment; filename=habilidades.csv'})
    if fmt == 'xlsx':
        data = export_skills_xlsx(skills)
        return Response(data,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        headers={'Content-Disposition': 'attachment; filename=habilidades.xlsx'})
    data = export_skills_text(skills).encode('utf-8')
    return Response(data, mimetype='text/plain; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename=habilidades.txt'})


# ─────────────────────────────────────────────────────────────────────────────
# Talents — CRUD
# ─────────────────────────────────────────────────────────────────────────────

@skills_talents_bp.route('/talentos')
def list_talents():
    search     = request.args.get('q', '').strip()
    search_all = request.args.get('search_all', '0') == '1'

    query = Talent.query
    if search:
        if search_all:
            query = query.filter(
                Talent.name_es.ilike(f'%{search}%')
                | Talent.name_en.ilike(f'%{search}%')
                | Talent.description.ilike(f'%{search}%')
            )
        else:
            query = query.filter(
                Talent.name_es.ilike(f'%{search}%') | Talent.name_en.ilike(f'%{search}%')
            )

    talents = query.order_by(Talent.name_es).all()
    return render_template('talents/list.html', talents=talents, search=search, search_all=search_all)


@skills_talents_bp.route('/talentos/<int:talent_id>')
def talent_detail(talent_id):
    talent   = Talent.query.get_or_404(talent_id)
    prof_ids = [pt.profession_id for pt in ProfessionTalent.query.filter_by(talent_id=talent_id).all()]
    professions = Profession.query.filter(Profession.id.in_(prof_ids)).order_by(Profession.name).all()
    return render_template('talents/detail.html', talent=talent, professions=professions)


@skills_talents_bp.route('/talentos/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def create_talent():
    if request.method == 'POST':
        talent = Talent(
            name_es=request.form.get('name_es', '').strip(),
            name_en=request.form.get('name_en', '').strip() or None,
            description=request.form.get('description', '').strip() or None,
            max_times=int(request.form.get('max_times', 1) or 1),
        )
        db.session.add(talent)
        db.session.commit()
        flash(f'Talento "{talent.name_es}" creado.', 'success')
        return redirect(url_for('skills_talents.list_talents'))
    return render_template('talents/form.html', talent=None)


@skills_talents_bp.route('/talentos/<int:talent_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_talent(talent_id):
    talent = Talent.query.get_or_404(talent_id)
    if request.method == 'POST':
        talent.name_es    = request.form.get('name_es', '').strip()
        talent.name_en    = request.form.get('name_en', '').strip() or None
        talent.description = request.form.get('description', '').strip() or None
        talent.max_times  = int(request.form.get('max_times', 1) or 1)
        db.session.commit()
        flash(f'Talento "{talent.name_es}" actualizado.', 'success')
        return redirect(url_for('skills_talents.list_talents'))
    return render_template('talents/form.html', talent=talent)


@skills_talents_bp.route('/talentos/<int:talent_id>/eliminar', methods=['POST'])
@login_required
@admin_required
def delete_talent(talent_id):
    talent = Talent.query.get_or_404(talent_id)
    name   = talent.name_es
    db.session.delete(talent)
    db.session.commit()
    flash(f'Talento "{name}" eliminado.', 'warning')
    return redirect(url_for('skills_talents.list_talents'))


# ─────────────────────────────────────────────────────────────────────────────
# Talents — Import / Export
# ─────────────────────────────────────────────────────────────────────────────

@skills_talents_bp.route('/talentos/importar', methods=['GET', 'POST'])
@login_required
@admin_required
def import_talents():
    if request.method == 'GET':
        return render_template('talents/import.html')

    f = request.files.get('file')
    if not f or not f.filename:
        flash('Selecciona un fichero.', 'danger')
        return redirect(request.url)

    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ('.txt', '.csv', '.xlsx', '.xls'):
        flash('Formato no soportado. Usa .txt, .csv o .xlsx.', 'danger')
        return redirect(request.url)

    from app.services.import_service import parse_talents
    try:
        entries = parse_talents(f.read(), ext)
    except Exception as e:
        flash(f'Error al leer el fichero: {e}', 'danger')
        return redirect(request.url)

    existing = {t.name_es.lower(): t for t in Talent.query.all()}
    created = updated = skipped = 0
    mode = request.form.get('mode', 'skip')

    for entry in entries:
        name_lower = entry.get('name_es', '').lower()
        if not name_lower:
            continue
        if name_lower in existing:
            if mode == 'update':
                t = existing[name_lower]
                if entry.get('description') is not None:
                    t.description = entry['description']
                updated += 1
            else:
                skipped += 1
        else:
            t = Talent(
                name_es=entry['name_es'],
                description=entry.get('description'),
            )
            db.session.add(t)
            created += 1

    db.session.commit()
    flash(f'Importación completada: {created} creados, {updated} actualizados, {skipped} omitidos.', 'success')
    return redirect(url_for('skills_talents.list_talents'))


@skills_talents_bp.route('/talentos/exportar')
@login_required
@admin_required
def export_talents():
    fmt     = request.args.get('f', 'txt').lower()
    talents = Talent.query.order_by(Talent.name_es).all()
    from app.services.import_service import export_talents_text, export_talents_csv, export_talents_xlsx

    if fmt == 'csv':
        data = export_talents_csv(talents)
        return Response(data, mimetype='text/csv; charset=utf-8-sig',
                        headers={'Content-Disposition': 'attachment; filename=talentos.csv'})
    if fmt == 'xlsx':
        data = export_talents_xlsx(talents)
        return Response(data,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        headers={'Content-Disposition': 'attachment; filename=talentos.xlsx'})
    data = export_talents_text(talents).encode('utf-8')
    return Response(data, mimetype='text/plain; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename=talentos.txt'})
