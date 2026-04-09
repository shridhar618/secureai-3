from __future__ import annotations

from datetime import datetime
from io import BytesIO

from sqlalchemy import inspect, text

from app import db


def ensure_admin_user_schema() -> None:
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "users" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    additions = {
        "login_count": "INTEGER DEFAULT 0",
        "failed_login_count": "INTEGER DEFAULT 0",
        "last_login_at": "DATETIME",
        "last_login_ip": "VARCHAR(64)",
    }
    changed = False
    for name, definition in additions.items():
        if name in columns:
            continue
        db.session.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))
        changed = True

    if changed:
        db.session.commit()


def build_users_pdf(users: list[dict]) -> bytes:
    lines = [
        "SecureAI Admin User Directory",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "Passwords are not included because plaintext credentials are not stored by the system.",
        "",
    ]
    for user in users:
        lines.extend([
            f"User: {user.get('username', '-')}",
            f"Email: {user.get('email', '-')}",
            f"Role: {user.get('role', '-')}",
            f"Active: {'Yes' if user.get('is_active') else 'No'}",
            f"Registered: {user.get('created_at', '-')}",
            f"Last login: {user.get('last_login_at', 'Never')}",
            f"Last login IP: {user.get('last_login_ip', '-') or '-'}",
            f"Login count: {user.get('login_count', 0)}",
            f"Failed login count: {user.get('failed_login_count', 0)}",
            f"Suspicious: {'Yes' if user.get('is_suspicious') else 'No'}",
            f"Face profile: {'Yes' if user.get('has_face_profile') else 'No'}",
            "",
        ])

    return _build_simple_pdf(lines)


def _escape_pdf_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _build_simple_pdf(lines: list[str]) -> bytes:
    buffer = BytesIO()
    objects = []

    content_lines = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
    for index, line in enumerate(lines):
        if index == 0:
            content_lines.append(f"({_escape_pdf_text(line)}) Tj")
        else:
            content_lines.append("T*")
            content_lines.append(f"({_escape_pdf_text(line)}) Tj")
    content_lines.append("ET")
    content_stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(f"<< /Length {len(content_stream)} >>\nstream\n".encode("latin-1") + content_stream + b"\nendstream")

    buffer.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(buffer.tell())
        buffer.write(f"{index} 0 obj\n".encode("latin-1"))
        buffer.write(obj)
        buffer.write(b"\nendobj\n")

    xref_start = buffer.tell()
    buffer.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
    buffer.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode("latin-1")
    )
    return buffer.getvalue()
