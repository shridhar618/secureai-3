from app import db
from datetime import datetime


class User(db.Model):
    __tablename__ = "users"

    id                   = db.Column(db.Integer, primary_key=True)
    username             = db.Column(db.String(80), unique=True, nullable=False)
    email                = db.Column(db.String(120), unique=True, nullable=False)
    password_hash        = db.Column(db.String(256), nullable=False)
    role                 = db.Column(db.String(80), nullable=False, default="intern")
    role_id              = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=True)
    created_at           = db.Column(db.DateTime, default=datetime.utcnow)
    is_active            = db.Column(db.Boolean, default=True)
    login_count          = db.Column(db.Integer, default=0)
    failed_login_count   = db.Column(db.Integer, default=0)
    last_login_at        = db.Column(db.DateTime, nullable=True)
    last_login_ip        = db.Column(db.String(64), nullable=True)
    role_ref             = db.relationship("Role", back_populates="users", lazy="joined")

    # v2: suspicious-user tracking ─────────────────────────────────────────
    sensitive_query_count = db.Column(db.Integer, default=0)   # cumulative sensitive queries
    is_suspicious         = db.Column(db.Boolean, default=False)
    flagged_at            = db.Column(db.DateTime, nullable=True)
    # ───────────────────────────────────────────────────────────────────────

    def to_dict(self):
        role_name = self.role_ref.name if self.role_ref else (self.role or "intern")
        permissions = self.role_ref.permissions if self.role_ref else {}
        return {
            "id":                   self.id,
            "username":             self.username,
            "email":                self.email,
            "role":                 role_name,
            "role_id":              self.role_id,
            "permissions":          permissions or {},
            "created_at":           self.created_at.isoformat(),
            "is_active":            self.is_active,
            "login_count":          self.login_count or 0,
            "failed_login_count":   self.failed_login_count or 0,
            "last_login_at":        self.last_login_at.isoformat() if self.last_login_at else None,
            "last_login_ip":        self.last_login_ip,
            "sensitive_query_count":self.sensitive_query_count,
            "is_suspicious":        self.is_suspicious,
            "flagged_at":           self.flagged_at.isoformat() if self.flagged_at else None,
            "has_face_profile":     bool(getattr(self, "face_profile", None)),
            "password_status":      "Stored securely as a hash. Plaintext password is not available.",
        }
