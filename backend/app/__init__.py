from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO
from dotenv import load_dotenv
import os
from importlib import import_module
import sys

load_dotenv()

db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO()


def get_socketio_async_mode():
    preferred_mode = os.getenv("SOCKETIO_ASYNC_MODE", "").strip().lower()
    if preferred_mode:
        return preferred_mode

    # eventlet currently breaks on Python 3.13+, so fall back automatically.
    if sys.version_info >= (3, 13):
        return "threading"

    try:
        import eventlet  # noqa: F401
    except Exception:
        return "threading"

    return "eventlet"


def create_app():
    app = Flask(__name__)

    # Config
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///secureai.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False  # No expiry for demo

    # Extensions
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    async_mode = get_socketio_async_mode()
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode=async_mode,
        logger=False,
        engineio_logger=False,
    )
    app.config["SOCKETIO_ASYNC_MODE"] = async_mode

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.chat import chat_bp
    from app.routes.logs import logs_bp
    from app.routes.users import users_bp
    from app.routes.messages import messages_bp
    from app.routes.attendance import attendance_bp
    from app.routes.roles import roles_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(chat_bp, url_prefix="/api")
    app.register_blueprint(logs_bp, url_prefix="/api")
    app.register_blueprint(users_bp, url_prefix="/api")
    app.register_blueprint(messages_bp, url_prefix="/api")
    app.register_blueprint(attendance_bp, url_prefix="/api")
    app.register_blueprint(roles_bp, url_prefix="/api")

    # Socket events
    from app.routes import socket_events  # noqa
    import_module("app.models")

    with app.app_context():
        from app.services.rbac import ensure_rbac_ready
        from app.services.admin_users import ensure_admin_user_schema

        db.create_all()
        ensure_admin_user_schema()
        ensure_rbac_ready()
        _seed_demo_users()

    return app


def _seed_demo_users():
    from app.models.user import User
    from app.services.rbac import get_or_fallback_role
    from werkzeug.security import generate_password_hash

    demo_users = [
        {"username": "admin", "email": "admin@secureai.com", "password": "admin123", "role": "admin"},
        {"username": "hr_jane", "email": "hr@secureai.com", "password": "hr123", "role": "hr"},
        {"username": "intern_bob", "email": "intern@secureai.com", "password": "intern123", "role": "intern"},
    ]
    for u in demo_users:
        if not User.query.filter_by(username=u["username"]).first():
            role = get_or_fallback_role(u["role"])
            user = User(
                username=u["username"],
                email=u["email"],
                password_hash=generate_password_hash(u["password"]),
                role=role.name if role else u["role"],
                role_id=role.id if role else None,
            )
            db.session.add(user)
    db.session.commit()
