from app.extensions import db

# ── Association tables ────────────────────────────────────────────────────────

user_permissions = db.Table(
    'user_permissions',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('permission_code', db.String(50), db.ForeignKey('permissions.code', ondelete='CASCADE'), primary_key=True),
)

template_permissions = db.Table(
    'template_permissions',
    db.Column('template_id', db.Integer, db.ForeignKey('permission_templates.id', ondelete='CASCADE'), primary_key=True),
    db.Column('permission_code', db.String(50), db.ForeignKey('permissions.code', ondelete='CASCADE'), primary_key=True),
)


# ── Models ────────────────────────────────────────────────────────────────────

class Permission(db.Model):
    __tablename__ = 'permissions'

    code        = db.Column(db.String(50),  primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    module      = db.Column(db.String(50),  nullable=False, index=True)

    def __repr__(self):
        return f'<Permission {self.code}>'


class PermissionTemplate(db.Model):
    __tablename__ = 'permission_templates'

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name        = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))

    permissions = db.relationship(
        'Permission',
        secondary='template_permissions',
        lazy='select',
        order_by='Permission.module, Permission.code',
    )

    def __repr__(self):
        return f'<PermissionTemplate {self.name}>'


# ── Seed data ─────────────────────────────────────────────────────────────────

# Ordered list of all permissions the app supports.
# Add new entries here as the app grows; seed_permissions() is idempotent.
ALL_PERMISSIONS = [
    # (code, name, description, module)
    ('professions.view',   'Ver profesiones',        'Consultar listado y detalle de profesiones',              'professions'),
    ('professions.edit',   'Editar profesiones',     'Crear, editar y eliminar profesiones',                    'professions'),
    ('professions.import', 'Importar desde PDF',     'Importar profesiones desde un PDF',                       'professions'),
    ('skills.view',        'Ver habilidades',        'Consultar habilidades y talentos',                        'skills'),
    ('skills.edit',        'Editar habilidades',     'Crear, editar y eliminar habilidades y talentos',         'skills'),
    ('pathfinder.use',     'Buscador de caminos',    'Buscar rutas entre profesiones',                          'pathfinder'),
    ('characters.view',    'Ver personajes',         'Consultar personajes propios',                            'characters'),
    ('characters.edit',    'Editar personajes',      'Crear y editar personajes propios',                       'characters'),
    ('users.manage',       'Gestionar usuarios',     'Asignar plantillas y permisos a otros usuarios (no convertir en admin)', 'admin'),
]

# Default templates seeded on first run.
DEFAULT_TEMPLATES = [
    # (name, description, [permission_codes])
    (
        'Lector',
        'Acceso de solo consulta a todas las secciones públicas',
        ['professions.view', 'skills.view', 'pathfinder.use', 'characters.view'],
    ),
    (
        'Editor',
        'Consulta y edición de contenido del juego',
        ['professions.view', 'professions.edit', 'professions.import',
         'skills.view', 'skills.edit', 'pathfinder.use',
         'characters.view', 'characters.edit'],
    ),
    (
        'Gestor',
        'Editor con capacidad de gestionar permisos de otros usuarios',
        ['professions.view', 'professions.edit', 'professions.import',
         'skills.view', 'skills.edit', 'pathfinder.use',
         'characters.view', 'characters.edit', 'users.manage'],
    ),
]


def seed_permissions_and_templates():
    """Idempotent: insert any missing permissions and create default templates."""
    for code, name, description, module in ALL_PERMISSIONS:
        if not db.session.get(Permission, code):
            db.session.add(Permission(
                code=code, name=name, description=description, module=module
            ))
    db.session.flush()

    for t_name, t_desc, codes in DEFAULT_TEMPLATES:
        if not PermissionTemplate.query.filter_by(name=t_name).first():
            perms = [db.session.get(Permission, c) for c in codes]
            perms = [p for p in perms if p]
            db.session.add(PermissionTemplate(
                name=t_name, description=t_desc, permissions=perms
            ))
    db.session.commit()
