from datetime import datetime
from flask_login import UserMixin
from app.extensions import db, bcrypt, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False, index=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(20),  nullable=False, default='user')  # 'admin' | 'user'
    active        = db.Column(db.Boolean,     default=True, nullable=False)
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)
    template_id   = db.Column(db.Integer, db.ForeignKey('permission_templates.id'), nullable=True)

    # Relationships
    characters = db.relationship('Character', backref='owner', lazy='dynamic')
    template   = db.relationship('PermissionTemplate', foreign_keys=[template_id], lazy='select')
    direct_permissions = db.relationship(
        'Permission',
        secondary='user_permissions',
        lazy='select',
    )

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_active(self):
        return self.active

    # ── Permission helpers ────────────────────────────────────────────────────

    def has_perm(self, code: str) -> bool:
        """True if the user holds the given permission. Admins bypass all checks."""
        if not self.is_authenticated:
            return False
        if self.is_admin:
            return True
        if any(p.code == code for p in self.direct_permissions):
            return True
        if self.template and any(p.code == code for p in self.template.permissions):
            return True
        return False

    def effective_perm_codes(self) -> set:
        """Return the set of all effective permission codes for this user."""
        if self.is_admin:
            return {'*'}
        codes = {p.code for p in self.direct_permissions}
        if self.template:
            codes |= {p.code for p in self.template.permissions}
        return codes

    # ── Auth helpers ──────────────────────────────────────────────────────────

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
