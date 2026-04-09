from __future__ import annotations

from sqlalchemy import inspect, text

from app import db


DEFAULT_ROLE_DEFINITIONS = [
    {
        "name": "admin",
        "permissions": {
            "allowed_intents": ["*"],
            "restricted_keywords": [],
            "mask_pii": False,
            "can_manage_roles": True,
        },
    },
    {
        "name": "hr",
        "permissions": {
            "allowed_intents": ["project_info", "hr_info", "attendance_info", "general_info"],
            "restricted_keywords": ["password", "secret", "api key", "private key", "credential"],
            "mask_pii": True,
            "can_manage_roles": False,
        },
    },
    {
        "name": "intern",
        "permissions": {
            "allowed_intents": ["project_info", "general_info", "attendance_info"],
            "restricted_keywords": [
                "salary",
                "compensation",
                "confidential",
                "proprietary",
                "social security",
                "ssn",
                "credit card",
                "bank account",
                "password",
                "credential",
                "secret",
                "api key",
                "private key",
            ],
            "mask_pii": False,
            "can_manage_roles": False,
        },
    },
    {
        "name": "developer",
        "permissions": {
            "allowed_intents": ["project_info", "security_info", "general_info"],
            "restricted_keywords": ["salary", "social security", "ssn", "credit card", "bank account"],
            "mask_pii": False,
            "can_manage_roles": False,
        },
    },
    {
        "name": "manager",
        "permissions": {
            "allowed_intents": ["project_info", "hr_info", "attendance_info", "general_info"],
            "restricted_keywords": ["password", "credential", "api key", "private key"],
            "mask_pii": False,
            "can_manage_roles": False,
        },
    },
    {
        "name": "team lead",
        "permissions": {
            "allowed_intents": ["project_info", "attendance_info", "general_info"],
            "restricted_keywords": ["salary", "social security", "ssn", "credit card", "bank account"],
            "mask_pii": False,
            "can_manage_roles": False,
        },
    },
    {
        "name": "finance",
        "permissions": {
            "allowed_intents": ["finance_info", "project_info", "general_info"],
            "restricted_keywords": ["password", "credential", "api key", "private key", "medical record"],
            "mask_pii": False,
            "can_manage_roles": False,
        },
    },
    {
        "name": "security analyst",
        "permissions": {
            "allowed_intents": ["security_info", "project_info", "general_info"],
            "restricted_keywords": ["salary", "social security", "ssn", "credit card", "bank account"],
            "mask_pii": False,
            "can_manage_roles": False,
        },
    },
]

DEFAULT_ROLE_NAMES = [item["name"] for item in DEFAULT_ROLE_DEFINITIONS]


def normalize_role_name(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def normalize_permissions(payload: dict | None) -> dict:
    payload = payload or {}
    allowed_intents = _normalize_string_list(payload.get("allowed_intents"))
    restricted_keywords = _normalize_string_list(payload.get("restricted_keywords"))
    normalized = {
        "allowed_intents": allowed_intents or ["general_info"],
        "restricted_keywords": restricted_keywords,
        "mask_pii": bool(payload.get("mask_pii", False)),
        "can_manage_roles": bool(payload.get("can_manage_roles", False)),
    }
    return normalized


def _normalize_string_list(values) -> list[str]:
    if isinstance(values, list):
        raw_values = values
    elif values is None:
        raw_values = []
    else:
        raw_values = [values]

    normalized = []
    seen = set()
    for item in raw_values:
        text_value = " ".join(str(item or "").strip().lower().split())
        if not text_value or text_value in seen:
            continue
        seen.add(text_value)
        normalized.append(text_value)
    return normalized


def ensure_role_schema() -> None:
    from app.models.role import Role

    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "roles" not in tables:
        Role.__table__.create(bind=db.engine, checkfirst=True)
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())

    if "users" not in tables:
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "role_id" not in user_columns:
        db.session.execute(text("ALTER TABLE users ADD COLUMN role_id INTEGER"))
        db.session.commit()


def seed_default_roles() -> None:
    from app.models.role import Role

    changed = False
    for definition in DEFAULT_ROLE_DEFINITIONS:
        role_name = normalize_role_name(definition["name"])
        permissions = normalize_permissions(definition.get("permissions"))
        role = Role.query.filter_by(name=role_name).first()
        if role is None:
            role = Role(name=role_name, permissions=permissions)
            db.session.add(role)
            changed = True
            continue

        if role.permissions != permissions:
            role.permissions = permissions
            changed = True

    if changed:
        db.session.commit()


def backfill_user_role_links() -> None:
    from app.models.role import Role
    from app.models.user import User

    roles_by_name = {role.name: role for role in Role.query.all()}
    default_role = roles_by_name.get("intern")
    changed = False

    for user in User.query.all():
        effective_name = normalize_role_name(getattr(user.role_ref, "name", None) or user.role or "intern")
        role = roles_by_name.get(effective_name) or default_role
        if role is None:
            continue
        if user.role_id != role.id:
            user.role_id = role.id
            changed = True
        if user.role != role.name:
            user.role = role.name
            changed = True

    if changed:
        db.session.commit()


def get_role_by_name(name: str | None):
    from app.models.role import Role

    ensure_rbac_ready()
    normalized = normalize_role_name(name)
    if not normalized:
        return None
    return Role.query.filter_by(name=normalized).first()


def get_or_fallback_role(name: str | None, fallback: str = "intern"):
    role = get_role_by_name(name)
    if role:
        return role
    return get_role_by_name(fallback)


def get_all_roles():
    from app.models.role import Role

    ensure_rbac_ready()
    return Role.query.order_by(Role.name.asc()).all()


def get_role_names() -> list[str]:
    return [role.name for role in get_all_roles()]


def get_user_role_name(user) -> str:
    if user is None:
        return "intern"
    return normalize_role_name(getattr(user.role_ref, "name", None) or getattr(user, "role", None) or "intern") or "intern"


def get_user_permissions(user) -> dict:
    role = getattr(user, "role_ref", None)
    if role and role.permissions:
        return normalize_permissions(role.permissions)

    role_by_name = get_or_fallback_role(getattr(user, "role", None))
    if role_by_name and role_by_name.permissions:
        return normalize_permissions(role_by_name.permissions)

    return normalize_permissions({})


def user_has_role(user, role_name: str) -> bool:
    return get_user_role_name(user) == normalize_role_name(role_name)


def user_has_any_role(user, role_names: tuple[str, ...] | list[str] | set[str]) -> bool:
    normalized_names = {normalize_role_name(name) for name in role_names}
    return get_user_role_name(user) in normalized_names


def ensure_rbac_ready() -> None:
    ensure_role_schema()
    seed_default_roles()
    backfill_user_role_links()
