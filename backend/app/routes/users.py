from flask import Blueprint, jsonify, make_response, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.models.user import User
from app.services.admin_users import build_users_pdf, ensure_admin_user_schema
from app.services.rbac import get_all_roles, get_role_by_name, user_has_role

users_bp = Blueprint("users", __name__)


def _current_user():
    user_id = int(get_jwt_identity())
    return User.query.get(user_id)


def _require_admin():
    user = _current_user()
    return user if user and user_has_role(user, "admin") else None


@users_bp.route("/users", methods=["GET"])
@jwt_required()
def list_users():
    """Return all users (for private chat user list)."""
    ensure_admin_user_schema()
    current_id = int(get_jwt_identity())
    users = User.query.filter(User.id != current_id, User.is_active == True).all()
    return jsonify({"users": [u.to_dict() for u in users]}), 200


@users_bp.route("/admin/users", methods=["GET"])
@jwt_required()
def admin_list_users():
    ensure_admin_user_schema()
    admin = _require_admin()
    if not admin:
        return jsonify({"error": "Admin access required"}), 403

    query = User.query.order_by(User.created_at.desc())
    search = request.args.get("search", "").strip().lower()
    role = request.args.get("role", "").strip().lower()
    status = request.args.get("status", "").strip().lower()

    users = query.all()
    if search:
        users = [
            user for user in users
            if search in user.username.lower() or search in user.email.lower()
        ]
    if role:
        users = [user for user in users if (user.to_dict().get("role") or "").lower() == role]
    if status == "active":
        users = [user for user in users if user.is_active]
    elif status == "inactive":
        users = [user for user in users if not user.is_active]

    return jsonify({
        "users": [user.to_dict() for user in users],
        "roles": [role_item.to_dict() for role_item in get_all_roles()],
        "summary": {
            "total_users": len(users),
            "active_users": sum(1 for user in users if user.is_active),
            "inactive_users": sum(1 for user in users if not user.is_active),
            "suspicious_users": sum(1 for user in users if user.is_suspicious),
            "users_with_face_profile": sum(1 for user in users if bool(getattr(user, "face_profile", None))),
        },
    }), 200


@users_bp.route("/admin/users/<int:user_id>", methods=["PATCH"])
@jwt_required()
def admin_update_user(user_id: int):
    ensure_admin_user_schema()
    admin = _require_admin()
    if not admin:
        return jsonify({"error": "Admin access required"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    if "is_active" in data:
        user.is_active = bool(data["is_active"])

    role_name = data.get("role")
    if role_name:
        role = get_role_by_name(role_name)
        if not role:
            return jsonify({"error": "Role not found"}), 404
        user.role = role.name
        user.role_id = role.id

    db.session.commit()
    return jsonify({"user": user.to_dict()}), 200


@users_bp.route("/admin/users/export/pdf", methods=["GET"])
@jwt_required()
def admin_export_users_pdf():
    ensure_admin_user_schema()
    admin = _require_admin()
    if not admin:
        return jsonify({"error": "Admin access required"}), 403

    users = [user.to_dict() for user in User.query.order_by(User.created_at.desc()).all()]
    pdf_data = build_users_pdf(users)
    response = make_response(pdf_data)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=secureai-admin-user-directory.pdf"
    return response
