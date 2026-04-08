import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4


BASE_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
IMPORT_DRAFTS_PATH = BASE_DATA_DIR / "imported_knowledge_drafts.json"
DEFAULT_ALLOWED_ROLES = ["admin", "hr", "intern"]
DEFAULT_REVIEW_STATUS = "draft"
TERMINAL_REVIEW_STATUSES = {"approved", "rejected"}


def list_imported_knowledge_drafts(review_status: str | None = None) -> list[dict]:
    drafts = _read_drafts()
    if review_status:
        drafts = [item for item in drafts if item.get("review_status") == review_status]
    drafts.sort(key=lambda item: item.get("imported_at", ""), reverse=True)
    return [serialize_imported_knowledge_draft(item) for item in drafts]


def get_imported_knowledge_draft(draft_id: str) -> dict | None:
    for item in _read_drafts():
        if str(item.get("id", "")).strip() == draft_id:
            return serialize_imported_knowledge_draft(item)
    return None


def serialize_imported_knowledge_draft(item: dict) -> dict:
    source_type = str(item.get("source_type", "import")).strip().lower() or "import"
    source_name = str(item.get("source_name", "")).strip()
    review_status = str(item.get("review_status", DEFAULT_REVIEW_STATUS)).strip() or DEFAULT_REVIEW_STATUS

    draft = {
        "id": str(item.get("id", "")).strip(),
        "question": str(item.get("question", "")).strip(),
        "answer": str(item.get("answer", "")).strip(),
        "category": str(item.get("category", "General")).strip() or "General",
        "keywords": _normalize_string_list(item.get("keywords", [])),
        "aliases": _normalize_string_list(item.get("aliases", [])),
        "allowed_roles": _normalize_roles(item.get("allowed_roles", DEFAULT_ALLOWED_ROLES)),
        "source_type": source_type,
        "source_name": source_name,
        "review_status": review_status,
        "imported_at": str(item.get("imported_at", "")).strip(),
        "source": {
            "type": source_type,
            "name": source_name,
        },
    }
    access_rationale = str(item.get("access_rationale", "")).strip()
    if access_rationale:
        draft["access_rationale"] = access_rationale
    if review_status in TERMINAL_REVIEW_STATUSES:
        draft["reviewed_at"] = str(item.get("reviewed_at", "")).strip() or None
        draft["reviewed_by"] = str(item.get("reviewed_by", "")).strip() or None
    if review_status == "approved":
        draft["active_question_id"] = str(item.get("active_question_id", "")).strip() or None
    return draft


def append_imported_knowledge_drafts(
    entries: list[dict],
    *,
    source_type: str = "import",
    source_name: str = "",
) -> list[dict]:
    if not isinstance(entries, list) or not entries:
        raise ValueError("Draft import payload must be a non-empty list")

    drafts = _read_drafts()
    appended = []
    imported_at = datetime.utcnow().isoformat()
    normalized_source_type = (source_type or "import").strip().lower() or "import"
    normalized_source_name = str(source_name or "").strip()

    for raw in entries:
        if not isinstance(raw, dict):
            raise ValueError("Each imported draft must be an object")

        question = str(raw.get("question", "")).strip()
        answer = str(raw.get("answer", "")).strip()
        if not question or not answer:
            raise ValueError("Each imported draft must include question and answer")

        draft = {
            "id": f"draft-{uuid4().hex[:12]}",
            "question": question,
            "answer": answer,
            "category": str(raw.get("category", "General")).strip() or "General",
            "keywords": _normalize_string_list(raw.get("keywords", [])),
            "aliases": _normalize_string_list(raw.get("aliases", [])),
            "allowed_roles": _normalize_roles(raw.get("allowed_roles", DEFAULT_ALLOWED_ROLES)),
            "access_rationale": str(raw.get("access_rationale", "")).strip(),
            "source_type": normalized_source_type,
            "source_name": normalized_source_name,
            "review_status": DEFAULT_REVIEW_STATUS,
            "imported_at": imported_at,
        }
        drafts.append(draft)
        appended.append(serialize_imported_knowledge_draft(draft))

    _write_drafts(drafts)
    return appended


def approve_imported_knowledge_draft(
    draft_id: str,
    *,
    reviewed_by: str,
    active_question_id: str,
) -> dict:
    return _transition_draft(
        draft_id,
        review_status="approved",
        reviewed_by=reviewed_by,
        active_question_id=active_question_id,
    )


def reject_imported_knowledge_draft(draft_id: str, *, reviewed_by: str) -> dict:
    return _transition_draft(
        draft_id,
        review_status="rejected",
        reviewed_by=reviewed_by,
    )


def build_active_question_from_draft(draft_id: str) -> dict:
    draft = _find_draft_record(draft_id)
    if not draft:
        raise ValueError("Draft not found")
    if str(draft.get("review_status", DEFAULT_REVIEW_STATUS)).strip() != DEFAULT_REVIEW_STATUS:
        raise ValueError("Only draft items can be reviewed")

    return {
        "question": str(draft.get("question", "")).strip(),
        "answer": str(draft.get("answer", "")).strip(),
        "category": str(draft.get("category", "General")).strip() or "General",
        "keywords": _normalize_string_list(draft.get("keywords", [])),
        "aliases": _normalize_string_list(draft.get("aliases", [])),
        "allowed_roles": _normalize_roles(draft.get("allowed_roles", DEFAULT_ALLOWED_ROLES)),
    }


def _read_drafts() -> list[dict]:
    _ensure_drafts_file()
    with IMPORT_DRAFTS_PATH.open("r", encoding="utf-8") as file_obj:
        data = json.load(file_obj)
    if not isinstance(data, list):
        raise ValueError("Imported knowledge drafts must be a list")
    return data


def _find_draft_record(draft_id: str) -> dict | None:
    for item in _read_drafts():
        if str(item.get("id", "")).strip() == draft_id:
            return item
    return None


def _transition_draft(
    draft_id: str,
    *,
    review_status: str,
    reviewed_by: str,
    active_question_id: str | None = None,
) -> dict:
    if review_status not in TERMINAL_REVIEW_STATUSES:
        raise ValueError("Invalid draft review status")

    drafts = _read_drafts()
    for item in drafts:
        if str(item.get("id", "")).strip() != draft_id:
            continue

        current_status = str(item.get("review_status", DEFAULT_REVIEW_STATUS)).strip() or DEFAULT_REVIEW_STATUS
        if current_status != DEFAULT_REVIEW_STATUS:
            raise ValueError("Only draft items can be reviewed")

        item["review_status"] = review_status
        item["reviewed_at"] = datetime.utcnow().isoformat()
        item["reviewed_by"] = str(reviewed_by or "").strip() or "system"
        if review_status == "approved":
            item["active_question_id"] = str(active_question_id or "").strip()
        else:
            item.pop("active_question_id", None)
        _write_drafts(drafts)
        return serialize_imported_knowledge_draft(item)

    raise ValueError("Draft not found")


def _write_drafts(drafts: list[dict]) -> None:
    _ensure_drafts_file()
    with IMPORT_DRAFTS_PATH.open("w", encoding="utf-8") as file_obj:
        json.dump(drafts, file_obj, indent=2)
        file_obj.write("\n")


def _ensure_drafts_file() -> None:
    BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not IMPORT_DRAFTS_PATH.exists():
        IMPORT_DRAFTS_PATH.write_text("[]\n", encoding="utf-8")


def _normalize_string_list(value: list[str] | str | None) -> list[str]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        items = []

    normalized = []
    seen = set()
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(text)
    return normalized


def _normalize_roles(value: list[str] | str | None) -> list[str]:
    allowed = {"admin", "hr", "intern"}
    normalized = [role.lower() for role in _normalize_string_list(value) if role.lower() in allowed]
    return normalized or DEFAULT_ALLOWED_ROLES.copy()
