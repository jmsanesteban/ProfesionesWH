import os
import click
from flask import Flask, flash, redirect, url_for, request
from app.config import config_by_name
from app.extensions import db, login_manager, bcrypt, migrate, csrf


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.professions import professions_bp
    from app.routes.skills_talents import skills_talents_bp
    from app.routes.pathfinder import pathfinder_bp
    from app.routes.characters import characters_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(professions_bp, url_prefix='/profesiones')
    app.register_blueprint(skills_talents_bp)
    app.register_blueprint(pathfinder_bp, url_prefix='/buscador')
    app.register_blueprint(characters_bp, url_prefix='/personajes')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Import models so Flask-Migrate detects them
    from app.models import user, permission, profession, skill, talent, character, synonym  # noqa: F401

    _register_cli_commands(app)
    _register_error_handlers(app)

    return app


def _register_error_handlers(app):
    from werkzeug.exceptions import RequestEntityTooLarge

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(e):
        max_mb = app.config.get('MAX_CONTENT_LENGTH', 52428800) // (1024 * 1024)
        flash(f'El archivo supera el tamaño máximo permitido ({max_mb} MB).', 'danger')
        referrer = request.referrer
        if referrer and '/admin/pdf' in referrer:
            return redirect(url_for('admin.pdf_upload')), 302
        return redirect('/'), 302


def _register_cli_commands(app):
    @app.cli.command('init-db')
    def init_db_cmd():
        """Create all database tables and apply incremental column additions."""
        with app.app_context():
            db.create_all()
            from sqlalchemy import text, inspect as sa_inspect
            inspector = sa_inspect(db.engine)
            skill_cols = {c['name'] for c in inspector.get_columns('skills')}
            with db.engine.begin() as conn:
                if 'caracteristicas' not in skill_cols:
                    conn.execute(text('ALTER TABLE skills ADD COLUMN caracteristicas VARCHAR(300) NULL'))
                    click.echo('  Added skills.caracteristicas')
                if 'talentos_asociados' not in skill_cols:
                    conn.execute(text('ALTER TABLE skills ADD COLUMN talentos_asociados VARCHAR(500) NULL'))
                    click.echo('  Added skills.talentos_asociados')
            # profession_skills / profession_talents: add id PK + specialization
            for tbl in ('profession_skills', 'profession_talents'):
                tbl_cols = {c['name'] for c in inspector.get_columns(tbl)}
                with db.engine.begin() as conn:
                    if 'id' not in tbl_cols:
                        try:
                            # MySQL blocks DROP PRIMARY KEY when the PK index is the only
                            # index covering a FK column. Add an explicit index on profession_id
                            # first so the FK constraint remains satisfied after PK removal.
                            existing_indexes = {
                                row[2] for row in conn.execute(
                                    text(f'SHOW INDEX FROM {tbl}')
                                ).fetchall()
                            }
                            if 'idx_prof_id' not in existing_indexes:
                                conn.execute(text(
                                    f'ALTER TABLE {tbl} '
                                    f'ADD INDEX idx_prof_id (profession_id)'
                                ))
                            conn.execute(text(f'ALTER TABLE {tbl} DROP PRIMARY KEY'))
                            conn.execute(text(
                                f'ALTER TABLE {tbl} '
                                f'ADD COLUMN id INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST'
                            ))
                            click.echo(f'  Migrated {tbl}: composite PK → id PK')
                        except Exception as e:
                            click.echo(f'  Warning ({tbl} PK migration): {e}')
                    if 'specialization' not in tbl_cols:
                        try:
                            conn.execute(text(
                                f'ALTER TABLE {tbl} ADD COLUMN specialization VARCHAR(150) NULL'
                            ))
                            click.echo(f'  Added {tbl}.specialization')
                        except Exception as e:
                            click.echo(f'  Warning ({tbl} specialization): {e}')

            # Incremental column: users.template_id (FK to permission_templates)
            user_cols = {c['name'] for c in inspector.get_columns('users')}
            with db.engine.begin() as conn:
                if 'template_id' not in user_cols:
                    conn.execute(text(
                        'ALTER TABLE users ADD COLUMN template_id INT NULL '
                        'REFERENCES permission_templates(id) ON DELETE SET NULL'
                    ))
                    click.echo('  Added users.template_id')

            click.echo('Database tables created/verified.')

            # Seed permissions and default templates (idempotent)
            from app.models.permission import seed_permissions_and_templates
            seed_permissions_and_templates()
            click.echo('  Permissions and templates seeded.')

            # Seed default synonyms on first run
            from app.models.synonym import Synonym, DEFAULT_SYNONYMS
            if Synonym.query.count() == 0:
                for source, target, is_prefix, notes in DEFAULT_SYNONYMS:
                    db.session.add(Synonym(
                        source=source, target=target,
                        is_prefix=is_prefix, notes=notes or None,
                    ))
                db.session.commit()
                click.echo(f'  Seeded {len(DEFAULT_SYNONYMS)} default synonyms.')

    @app.cli.command('create-admin')
    def create_admin_cmd():
        """Create the default admin user from environment config."""
        with app.app_context():
            from app.utils import create_default_admin
            create_default_admin()
            click.echo('Admin creation complete.')
