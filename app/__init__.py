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
    from app.models import user, profession, skill, talent, character  # noqa: F401

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
            click.echo('Database tables created/verified.')

    @app.cli.command('create-admin')
    def create_admin_cmd():
        """Create the default admin user from environment config."""
        with app.app_context():
            from app.utils import create_default_admin
            create_default_admin()
            click.echo('Admin creation complete.')
