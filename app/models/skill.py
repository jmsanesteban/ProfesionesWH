from datetime import datetime
from app.extensions import db


class Skill(db.Model):
    __tablename__ = 'skills'

    id = db.Column(db.Integer, primary_key=True)
    name_es = db.Column(db.String(150), nullable=False, index=True)
    name_en = db.Column(db.String(150), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_advanced          = db.Column(db.Boolean, default=False, nullable=False)
    caracteristicas      = db.Column(db.String(300), nullable=True)
    talentos_asociados   = db.Column(db.String(500), nullable=True)
    created_at           = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Skill {self.name_es}>'
