from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request

from app import db
from app.models.role import Role
from app.models.user import User
from app.services.rbac import (
    ensure_rbac_ready,
    get_all_roles,
    normalize_permissions,
    normalize_role_name,
    user_has_role,
)

roles_bp = Blueprint("roles", __name__)


def _current_user():
    try:
        verify_jwt_in_request(optional=True)
    except Exception:
        return None

    identity = get_jwt_identity()
    if not identity:
        return None
    return User.query.get(int(identity))


def _require_admin():
    user = _current_user()
    return user if user and user_has_role(user, "admin") else None


@roles_bp.route("/roles", methods=["GET"])
def list_roles():
    ensure_rbac_ready()
    roles = [role.to_dict() for role in get_all_roles()]
    return jsonify({"roles": roles}), 200


@roles_bp.route("/roles", methods=["POST"])
@jwt_required()
def create_role():
    admin = _require_admin()
    if not admin:
        return jsonify({"error": "Admin access required"}), 403

    ensure_rbac_ready()
    data = request.get_json() or {}
    name = normalize_role_name(data.get("name"))
    if not name:
        return jsonify({"error": "Role name is required"}), 400
    if Role.query.filter_by(name=name).first():
        return jsonify({"error": "Role already exists"}), 409

    role = Role(
        name=name,
        permissions=normalize_permissions(data.get("permissions")),
    )
    db.session.add(role)
    db.session.commit()
    return jsonify({"role": role.to_dict()}), 201


@roles_bp.route("/roles/<int:role_id>", methods=["PUT"])
@jwt_required()
def update_role(role_id):
    admin = _require_admin()
    if not admin:
        return jsonify({"error": "Admin access required"}), 403

    ensure_rbac_ready()
    role = Role.query.get(role_id)
    if not role:
        return jsonify({"error": "Role not found"}), 404

    data = request.get_json() or {}
    name = normalize_role_name(data.get("name", role.name))
    if not name:
        return jsonify({"error": "Role name is required"}), 400

    existing = Role.query.filter_by(name=name).first()
    if existing and existing.id != role.id:
        return jsonify({"error": "Role name already exists"}), 409

    old_name = role.name
    role.name = name
    role.permissions = normalize_permissions(data.get("permissions", role.permissions))

    if old_name != role.name:
        for user in User.query.filter_by(role_id=role.id).all():
            user.role = role.name

    db.session.commit()
    return jsonify({"role": role.to_dict()}), 200


@roles_bp.route("/roles/<int:role_id>", methods=["DELETE"])
@jwt_required()
def delete_role(role_id):
    admin = _require_admin()
    if not admin:
        return jsonify({"error": "Admin access required"}), 403

    ensure_rbac_ready()
    role = Role.query.get(role_id)
    if not role:
        return jsonify({"error": "Role not found"}), 404
    if role.name == "admin":
        return jsonify({"error": "The admin role cannot be deleted"}), 400
    if role.users:
        return jsonify({"error": "Reassign users before deleting this role"}), 409

    db.session.delete(role)
    db.session.commit()
    return jsonify({"message": "Role deleted"}), 200
