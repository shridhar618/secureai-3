"""
Modular AI service layer.
Supports OpenAI (GPT) and Google Gemini.
Falls back to a mock response if no API key is set (demo mode).
Also powers the local question bank, review queue, and dataset history.
"""

import csv
import io
import json
import logging
import os
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are SecureAI, an enterprise assistant. "
    "Be helpful, professional, and concise. "
    "Never refuse reasonable workplace questions."
)

BASE_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
QUESTION_BANK_PATH = BASE_DATA_DIR / "mock_question_bank.json"
QUESTION_HISTORY_PATH = BASE_DATA_DIR / "mock_question_bank_history.json"
UNANSWERED_QUEUE_PATH = BASE_DATA_DIR / "unanswered_questions.json"

DEFAULT_ALLOWED_ROLES = ["admin", "hr", "intern"]
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a", "an", "and", "are", "can", "do", "does", "for", "here", "how", "i",
    "in", "is", "me", "my", "of", "our", "the", "to", "what", "when", "with",
    "work", "you",
}
_ML_MATCH_THRESHOLD = 0.28
_HEURISTIC_MATCH_THRESHOLD = 6


def get_ai_response(messages: list[dict]) -> str:
    """
    Dispatch to the configured AI provider.
    `messages` is a list of {role, content} dicts (OpenAI format).
    """
    provider = os.getenv("AI_PROVIDER", "gemini").lower()

    if provider == "openai":
        return _openai_response(messages)
    if provider == "gemini":
        return _gemini_response(messages)
    return _mock_response(messages)


def list_mock_questions(role: str | None = None) -> list[dict]:
    question_bank = _filter_by_role(_load_question_bank(), role)
    return [serialize_question(item) for item in question_bank]


def get_question(question_id: str) -> dict | None:
    for item in _load_question_bank():
        if item["id"] == question_id:
            return dict(item)
    return None


def add_mock_question(
    question: str,
    answer: str,
    category: str = "General",
    keywords: list[str] | None = None,
    allowed_roles: list[str] | None = None,
    actor: str | None = None,
) -> dict:
    normalized_question = question.strip()
    normalized_answer = answer.strip()
    normalized_category = category.strip() or "General"
    normalized_keywords = _normalize_keywords(keywords or _extract_keywords(normalized_question))
    normalized_roles = _normalize_roles(allowed_roles)

    if not normalized_question:
        raise ValueError("Question is required")
    if not normalized_answer:
        raise ValueError("Answer is required")

    question_bank = _read_question_bank()
    entry = {
        "id": _build_unique_id(normalized_question, question_bank),
        "category": normalized_category,
        "question": normalized_question,
        "keywords": normalized_keywords,
        "allowed_roles": normalized_roles,
        "answer": normalized_answer,
    }
    question_bank.append(entry)
    _write_question_bank(question_bank)
    _append_history("create", entry["id"], actor=actor, after=entry)
    _clear_caches()
    return serialize_question(entry)


def update_mock_question(
    question_id: str,
    *,
    question: str,
    answer: str,
    category: str,
    keywords: list[str] | None = None,
    allowed_roles: list[str] | None = None,
    actor: str | None = None,
) -> dict:
    question_bank = _read_question_bank()
    for index, item in enumerate(question_bank):
        if item.get("id") != question_id:
            continue

        before = _normalize_question_record(item)
        updated = {
            "id": before["id"],
            "category": category.strip() or "General",
            "question": question.strip(),
            "keywords": _normalize_keywords(keywords or _extract_keywords(question)),
            "allowed_roles": _normalize_roles(allowed_roles),
            "answer": answer.strip(),
        }
        if not updated["question"]:
            raise ValueError("Question is required")
        if not updated["answer"]:
            raise ValueError("Answer is required")

        question_bank[index] = updated
        _write_question_bank(question_bank)
        _append_history("update", question_id, actor=actor, before=before, after=updated)
        _clear_caches()
        return serialize_question(updated, include_answer=True)

    raise ValueError("Question not found")


def delete_mock_question(question_id: str, actor: str | None = None) -> None:
    question_bank = _read_question_bank()
    new_bank = []
    removed = None
    for item in question_bank:
        if item.get("id") == question_id:
            removed = _normalize_question_record(item)
            continue
        new_bank.append(item)

    if removed is None:
        raise ValueError("Question not found")

    _write_question_bank(new_bank)
    _append_history("delete", question_id, actor=actor, before=removed)
    _clear_caches()


def import_mock_questions(entries: list[dict], actor: str | None = None) -> dict:
    if not isinstance(entries, list) or not entries:
        raise ValueError("Import payload must be a non-empty list")

    question_bank = _read_question_bank()
    imported = []
    for raw in entries:
        if not isinstance(raw, dict):
            raise ValueError("Each imported question must be an object")

        question = str(raw.get("question", "")).strip()
        answer = str(raw.get("answer", "")).strip()
        category = str(raw.get("category", "General")).strip() or "General"
        keywords = raw.get("keywords", [])
        allowed_roles = raw.get("allowed_roles", DEFAULT_ALLOWED_ROLES)
        if not question or not answer:
            raise ValueError("Each imported question must include question and answer")

        entry = {
            "id": _build_unique_id(question, question_bank),
            "category": category,
            "question": question,
            "keywords": _normalize_keywords(keywords or _extract_keywords(question)),
            "allowed_roles": _normalize_roles(allowed_roles),
            "answer": answer,
        }
        question_bank.append(entry)
        imported.append(entry)
        _append_history("import", entry["id"], actor=actor, after=entry)

    _write_question_bank(question_bank)
    _clear_caches()
    return {
        "count": len(imported),
        "questions": [serialize_question(item) for item in imported],
    }


def export_mock_questions_csv(role: str | None = None) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["id", "category", "question", "keywords", "allowed_roles", "answer"])
    writer.writeheader()
    for item in _filter_by_role(_load_question_bank(), role):
        writer.writerow({
            "id": item["id"],
            "category": item["category"],
            "question": item["question"],
            "keywords": ", ".join(item["keywords"]),
            "allowed_roles": ", ".join(item["allowed_roles"]),
            "answer": item["answer"],
        })
    return buffer.getvalue()


def list_question_history(limit: int = 100) -> list[dict]:
    history = _read_json_array(QUESTION_HISTORY_PATH)
    history.reverse()
    return history[:limit]


def list_unanswered_questions(status: str | None = None) -> list[dict]:
    unresolved = _read_json_array(UNANSWERED_QUEUE_PATH)
    if status:
        unresolved = [item for item in unresolved if item.get("status") == status]
    unresolved.sort(key=lambda item: item.get("last_seen_at", ""), reverse=True)
    return unresolved


def capture_unanswered_question(query: str, role: str, username: str) -> dict:
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Query is required")

    queue = _read_json_array(UNANSWERED_QUEUE_PATH)
    now = datetime.utcnow().isoformat()
    for item in queue:
        if item.get("query", "").strip().lower() == normalized_query.lower():
            item["count"] = int(item.get("count", 1)) + 1
            item["last_seen_at"] = now
            item["latest_role"] = role
            item["latest_username"] = username
            _write_json_array(UNANSWERED_QUEUE_PATH, queue)
            return item

    entry = {
        "id": _build_queue_id(normalized_query),
        "query": normalized_query,
        "count": 1,
        "status": "open",
        "created_at": now,
        "last_seen_at": now,
        "latest_role": role,
        "latest_username": username,
        "resolution_note": "",
    }
    queue.append(entry)
    _write_json_array(UNANSWERED_QUEUE_PATH, queue)
    return entry


def resolve_unanswered_question(queue_id: str, status: str, resolution_note: str = "") -> dict:
    valid_statuses = {"open", "resolved", "ignored"}
    if status not in valid_statuses:
        raise ValueError("Invalid queue status")

    queue = _read_json_array(UNANSWERED_QUEUE_PATH)
    for item in queue:
        if item.get("id") == queue_id:
            item["status"] = status
            item["resolution_note"] = resolution_note.strip()
            item["resolved_at"] = datetime.utcnow().isoformat() if status != "open" else None
            _write_json_array(UNANSWERED_QUEUE_PATH, queue)
            return item
    raise ValueError("Queue item not found")


def find_question_match_for_query(query: str, role: str | None = None) -> dict | None:
    return _match_question(query, role)


def infer_question_category(query: str) -> str | None:
    matched = _match_question(query, role=None)
    return matched["category"] if matched else None


def get_suggested_questions(query: str, role: str | None = None, limit: int = 4) -> list[dict]:
    candidates = _filter_by_role(_load_question_bank(), role)
    if not candidates:
        return []

    matched = _match_question(query, role)
    suggestions = []
    seen = set()

    if matched:
        for item in candidates:
            if item["id"] == matched["id"]:
                continue
            if item["category"] == matched["category"] or set(item["keywords"]) & set(matched["keywords"]):
                suggestions.append(serialize_question(item))
                seen.add(item["id"])
                if len(suggestions) >= limit:
                    return suggestions

    for item in candidates:
        if item["id"] in seen:
            continue
        suggestions.append(serialize_question(item))
        if len(suggestions) >= limit:
            break
    return suggestions


def get_question_bank_analytics(logs: list[dict], feedback_rows: list[dict]) -> dict:
    questions = _load_question_bank()
    question_map = {item["question"].lower(): item for item in questions}
    counts = {}
    blocked_by_role = {}

    for log in logs:
        query_text = str(log.get("query", "")).strip().lower()
        if query_text in question_map:
            item = question_map[query_text]
            counts[item["question"]] = counts.get(item["question"], 0) + 1

        role = log.get("role", "unknown")
        if log.get("status") == "blocked":
            blocked_by_role[role] = blocked_by_role.get(role, 0) + 1

    top_questions = sorted(
        [{"question": question, "count": count} for question, count in counts.items()],
        key=lambda item: (-item["count"], item["question"].lower()),
    )[:5]

    unhelpful_counts = {}
    for row in feedback_rows:
        if row.get("value") != "unhelpful":
            continue
        query_text = str(row.get("query", "")).strip()
        if not query_text:
            continue
        unhelpful_counts[query_text] = unhelpful_counts.get(query_text, 0) + 1

    low_quality = sorted(
        [{"query": query, "count": count} for query, count in unhelpful_counts.items()],
        key=lambda item: (-item["count"], item["query"].lower()),
    )[:5]

    unanswered = list_unanswered_questions()
    open_unanswered = [item for item in unanswered if item.get("status") == "open"]

    return {
        "question_bank_total": len(questions),
        "top_questions": top_questions,
        "blocked_by_role": blocked_by_role,
        "unanswered_count": len(open_unanswered),
        "open_unanswered": open_unanswered[:5],
        "low_quality_responses": low_quality,
    }


def serialize_question(item: dict, *, include_answer: bool = False) -> dict:
    result = {
        "id": item["id"],
        "category": item["category"],
        "question": item["question"],
        "keywords": item["keywords"],
        "allowed_roles": item["allowed_roles"],
    }
    if include_answer:
        result["answer"] = item["answer"]
    return result


def _openai_response(messages: list[dict]) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("your-"):
        return _mock_response(messages)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=full_messages,
            max_tokens=800,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("OpenAI error: %s", exc)
        return _fallback_error(str(exc))


def _gemini_response(messages: list[dict]) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key.startswith("your-"):
        return _mock_response(messages)

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT,
        )
        history = []
        last_user_msg = ""
        for message in messages:
            if message["role"] == "user":
                last_user_msg = message["content"]
                history.append({"role": "user", "parts": [message["content"]]})
            elif message["role"] == "assistant":
                history.append({"role": "model", "parts": [message["content"]]})

        chat = model.start_chat(history=history[:-1] if history else [])
        response = chat.send_message(last_user_msg)
        return response.text.strip()
    except Exception as exc:
        logger.error("Gemini error: %s", exc)
        return _fallback_error(str(exc))


def _mock_response(messages: list[dict]) -> str:
    query = ""
    for message in reversed(messages):
        if message.get("role") == "user":
            query = message.get("content", "").lower()
            break

    matched_entry = _match_question(query)
    if matched_entry:
        return matched_entry["answer"]

    return (
        "I'm SecureAI running in demo mode (no API key configured). "
        "I could not find a strong dataset match for that question yet, so I logged it for admin review. "
        "Please configure an AI provider in .env for full open-ended responses."
    )


def _fallback_error(err: str) -> str:
    return (
        "I encountered an issue connecting to the AI provider. "
        "Please check your API key configuration. "
        f"Technical detail: {err[:120]}"
    )


@lru_cache(maxsize=1)
def _load_question_bank() -> list[dict]:
    _ensure_data_files()
    return [_normalize_question_record(item) for item in _read_question_bank()]


@lru_cache(maxsize=1)
def _get_question_bank_index() -> dict | None:
    question_bank = _load_question_bank()
    if not question_bank:
        return None

    documents = [_build_training_text(item) for item in question_bank]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    matrix = vectorizer.fit_transform(documents)
    return {
        "questions": question_bank,
        "vectorizer": vectorizer,
        "matrix": matrix,
    }


def _read_question_bank() -> list[dict]:
    _ensure_data_files()
    with QUESTION_BANK_PATH.open("r", encoding="utf-8") as file_obj:
        data = json.load(file_obj)
    if not isinstance(data, list):
        raise ValueError("Mock question bank must be a list")
    return data


def _write_question_bank(question_bank: list[dict]) -> None:
    _ensure_data_files()
    with QUESTION_BANK_PATH.open("w", encoding="utf-8") as file_obj:
        json.dump(question_bank, file_obj, indent=2)
        file_obj.write("\n")


def _match_question(query: str, role: str | None = None) -> dict | None:
    query_text = (query or "").strip().lower()
    if not query_text:
        return None

    ml_match = _match_question_with_ml(query_text, role)
    if ml_match:
        return ml_match

    return _match_question_with_heuristics(query_text, role)


def _match_question_with_ml(query_text: str, role: str | None = None) -> dict | None:
    index = _get_question_bank_index()
    if not index:
        return None

    filtered_questions = _filter_by_role(index["questions"], role)
    if not filtered_questions:
        return None

    query_vector = index["vectorizer"].transform([query_text])
    similarities = cosine_similarity(query_vector, index["matrix"]).ravel()
    ranked_indices = np.argsort(similarities)[::-1]

    allowed_ids = {item["id"] for item in filtered_questions}

    for index_value in ranked_indices:
        item = index["questions"][int(index_value)]
        if item["id"] not in allowed_ids:
            continue

        score = float(similarities[int(index_value)])
        if score >= _ML_MATCH_THRESHOLD:
            return item

    return None


def _match_question_with_heuristics(query_text: str, role: str | None = None) -> dict | None:
    query_tokens = set(_extract_keywords(query_text))
    best_match = None
    best_score = 0

    for item in _filter_by_role(_load_question_bank(), role):
        score = 0
        question_text = item["question"].lower()

        if query_text == question_text:
            score += 100
        elif question_text in query_text or query_text in question_text:
            score += 30

        for keyword in item["keywords"]:
            keyword_text = keyword.lower()
            if keyword_text and _keyword_in_text(keyword_text, query_text):
                score += 10

        question_tokens = set(_extract_keywords(question_text))
        score += len(query_tokens & question_tokens) * 2

        if score > best_score:
            best_score = score
            best_match = item

    return best_match if best_score >= _HEURISTIC_MATCH_THRESHOLD else None


def _filter_by_role(question_bank: list[dict], role: str | None) -> list[dict]:
    if not role:
        return question_bank
    return [item for item in question_bank if role in item["allowed_roles"]]


def _normalize_question_record(item: dict) -> dict:
    return {
        "id": str(item["id"]),
        "category": str(item.get("category", "General")).strip() or "General",
        "question": str(item["question"]).strip(),
        "keywords": _normalize_keywords(item.get("keywords", [])),
        "allowed_roles": _normalize_roles(item.get("allowed_roles", DEFAULT_ALLOWED_ROLES)),
        "answer": str(item["answer"]).strip(),
    }


def _append_history(action: str, question_id: str, *, actor: str | None, before: dict | None = None, after: dict | None = None) -> None:
    history = _read_json_array(QUESTION_HISTORY_PATH)
    history.append({
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "question_id": question_id,
        "actor": actor or "system",
        "before": before,
        "after": after,
    })
    _write_json_array(QUESTION_HISTORY_PATH, history)


def _ensure_data_files() -> None:
    BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for path in (QUESTION_HISTORY_PATH, UNANSWERED_QUEUE_PATH):
        if not path.exists():
            _write_json_array(path, [])


def _read_json_array(path: Path) -> list[dict]:
    _ensure_data_files()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file_obj:
        data = json.load(file_obj)
    return data if isinstance(data, list) else []


def _write_json_array(path: Path, values: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        json.dump(values, file_obj, indent=2)
        file_obj.write("\n")


def _clear_caches() -> None:
    _load_question_bank.cache_clear()
    _get_question_bank_index.cache_clear()


def _build_unique_id(question: str, question_bank: list[dict]) -> str:
    existing_ids = {str(item.get("id", "")).strip() for item in question_bank}
    slug = "-".join(_tokenize(question)) or "question"
    candidate = slug
    suffix = 2
    while candidate in existing_ids:
        candidate = f"{slug}-{suffix}"
        suffix += 1
    return candidate


def _build_queue_id(query: str) -> str:
    return f"{'-'.join(_tokenize(query))[:40] or 'question'}-{int(datetime.utcnow().timestamp())}"


def _normalize_keywords(keywords: list[str]) -> list[str]:
    cleaned = []
    seen = set()
    for keyword in keywords:
        value = str(keyword).strip().lower()
        if value and value not in seen:
            cleaned.append(value)
            seen.add(value)
    return cleaned


def _normalize_roles(roles: list[str] | None) -> list[str]:
    normalized = []
    seen = set()
    raw_roles = roles or DEFAULT_ALLOWED_ROLES
    for role in raw_roles:
        value = str(role).strip().lower()
        if value in {"admin", "hr", "intern"} and value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized or DEFAULT_ALLOWED_ROLES.copy()


def _build_training_text(item: dict) -> str:
    keyword_text = " ".join(item["keywords"])
    return f"{item['question']} {keyword_text} {keyword_text}"


def _keyword_in_text(keyword: str, text: str) -> bool:
    keyword_tokens = _tokenize(keyword)
    text_tokens = _tokenize(text)
    if not keyword_tokens or not text_tokens:
        return False

    if len(keyword_tokens) == 1:
        return keyword_tokens[0] in set(text_tokens)

    window_size = len(keyword_tokens)
    for index in range(len(text_tokens) - window_size + 1):
        if text_tokens[index:index + window_size] == keyword_tokens:
            return True
    return False


def _extract_keywords(question: str) -> list[str]:
    return [token for token in _tokenize(question) if token not in _STOP_WORDS]


def _tokenize(text: str) -> list[str]:
    return [token for token in _TOKEN_PATTERN.findall(text.lower()) if token]
