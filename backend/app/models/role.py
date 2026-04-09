from datetime import datetime

from app import db


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    permissions = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    users = db.relationship("User", back_populates="role_ref", lazy=True)

    def to_dict(self):
        permissions = self.permissions or {}
        return {
            "id": self.id,
            "name": self.name,
            "permissions": permissions,
            "allowed_intents": permissions.get("allowed_intents", []),
            "restricted_keywords": permissions.get("restricted_keywords", []),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
