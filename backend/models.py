"""
LUMA Database Models
SQLite via SQLAlchemy
"""

import json
import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    generations = db.relationship('Generation', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password: str):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify user password hash"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Generation(db.Model):
    __tablename__ = 'generations'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    prompt = db.Column(db.Text, nullable=False)
    negative_prompt = db.Column(db.Text, nullable=True)
    mode = db.Column(db.String(20), default='txt2img', nullable=False) # 'txt2img' or 'img2img'
    image_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='PENDING', nullable=False, index=True) # PENDING, PROCESSING, COMPLETED, FAILED
    error_message = db.Column(db.Text, nullable=True)
    parameters_json = db.Column(db.Text, nullable=True) # Serialized dictionary of params
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @property
    def parameters(self):
        if self.parameters_json:
            try:
                return json.loads(self.parameters_json)
            except Exception:
                return {}
        return {}

    @parameters.setter
    def parameters(self, value):
        if value is not None:
            self.parameters_json = json.dumps(value)
        else:
            self.parameters_json = None

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'prompt': self.prompt,
            'negative_prompt': self.negative_prompt,
            'mode': self.mode,
            'image_url': f"/api/images/{self.image_path}" if self.image_path else None,
            'status': self.status,
            'error_message': self.error_message,
            'parameters': self.parameters,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
