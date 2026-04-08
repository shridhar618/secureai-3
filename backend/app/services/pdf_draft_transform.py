import json
import logging
import os
import re
from typing import Any


logger = logging.getLogger(__name__)

DEFAULT_ALLOWED_ROLES = ["admin", "hr", "intern"]
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "we",
    "what", "when", "with", "you", "your",
}
_CATEGORY_KEYWORDS = {
    "Admin": {"admin", "audit", "governance", "compliance"},
    "HR": {"employee", "hr", "leave", "benefits", "onboarding", "attendance", "manager"},
    "IT": {"it", "system", "software", "vpn", "device", "access", "password"},
    "Security": {"security", "incident", "breach", "phishing", "mfa", "confidential"},
    "Finance": {"finance", "expense", "payroll", "budget", "invoice", "procurement"},
    "Operations": {"office", "travel", "visitor", "schedule", "operations", "workplace"},
}


def transform_pdf_text_to_candidate_entries(extracted_text: str) -> tuple[list[dict], dict]:
    normalized_text = _normalize_text(extracted_text)
    if not normalized_text:
        raise ValueError("Could not extract readable text from the PDF")

    ai_entries, ai_metadata = _transform_with_ai(normalized_text)
    if ai_entries:
        return ai_entries, ai_metadata

    fallback_entries = _transform_with_fallback(normalized_text)
    if fallback_entries:
        return fallback_entries, {
            "parse_mode": "deterministic_fallback",
            "detected_count": len(fallback_entries),
            "ai_provider": ai_metadata.get("ai_provider"),
            "ai_status": ai_metadata.get("ai_status"),
        }

    raise ValueError(
        "Could not transform PDF text into draft entries. Use a clearer PDF or provide labeled sections with enough text."
    )


def _transform_with_ai(extracted_text: str) -> tuple[list[dict], dict]:
    provider = os.getenv("AI_PROVIDER", "gemini").lower()
    prompt = _build_transformation_prompt(extracted_text)

    if provider == "openai":
        raw_output = _call_openai(prompt)
    elif provider == "gemini":
        raw_output = _call_gemini(prompt)
    else:
        raw_output = ""

    if not raw_output:
        return [], {"ai_provider": provider, "ai_status": "unavailable"}

    payload = _extract_json_payload(raw_output)
    if payload is None:
        logger.warning("PDF draft transform returned non-JSON AI output")
        return [], {"ai_provider": provider, "ai_status": "invalid_json"}

    entries = payload if isinstance(payload, list) else payload.get("questions", [])
    normalized_entries = _normalize_entries(entries)
    if not normalized_entries:
        return [], {"ai_provider": provider, "ai_status": "no_valid_entries"}

    return normalized_entries, {
        "parse_mode": "ai_structured",
        "detected_count": len(normalized_entries),
        "ai_provider": provider,
        "ai_status": "ok",
    }


def _call_openai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("your-"):
        return ""

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_PDF_DRAFT_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "Convert enterprise PDF text into structured knowledge draft entries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=1600,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("OpenAI PDF draft transform failed: %s", exc)
        return ""


def _call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key.startswith("your-"):
        return ""

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=os.getenv("GEMINI_PDF_DRAFT_MODEL", "gemini-1.5-flash"),
            system_instruction="Convert enterprise PDF text into structured knowledge draft entries.",
        )
        response = model.generate_content(prompt)
        return (response.text or "").strip()
    except Exception as exc:
        logger.warning("Gemini PDF draft transform failed: %s", exc)
        return ""


def _build_transformation_prompt(extracted_text: str) -> str:
    limited_text = extracted_text[:12000]
    return (
        "Return only valid JSON. "
        "Format: {\"questions\": [{\"question\": str, \"answer\": str, \"category\": str, "
        "\"keywords\": [str], \"aliases\": [str], \"allowed_roles\": [str]}]}.\n"
        "Rules:\n"
        "- Propose review-ready enterprise knowledge entries from the source text.\n"
        "- Keep answers grounded in the source text.\n"
        "- allowed_roles must be explicit and conservative. If uncertain, use [\"admin\", \"hr\", \"intern\"].\n"
        "- Do not invent facts not supported by the source.\n"
        "- Return 1 to 8 high-value entries.\n\n"
        f"Source text:\n{limited_text}"
    )


def _extract_json_payload(raw_output: str) -> Any | None:
    raw_output = (raw_output or "").strip()
    if not raw_output:
        return None

    decoder = json.JSONDecoder()
    for start in [index for index in (raw_output.find("{"), raw_output.find("[")) if index != -1]:
        try:
            payload, _ = decoder.raw_decode(raw_output[start:])
            return payload
        except json.JSONDecodeError:
            continue
    return None


def _transform_with_fallback(extracted_text: str) -> list[dict]:
    blocks = _split_blocks(extracted_text)
    entries = []
    seen_questions = set()

    for block in blocks:
        candidate = _build_fallback_entry(block)
        if not candidate:
            continue
        question_key = candidate["question"].lower()
        if question_key in seen_questions:
            continue
        seen_questions.add(question_key)
        entries.append(candidate)
        if len(entries) >= 8:
            break

    return entries


def _split_blocks(extracted_text: str) -> list[str]:
    normalized = extracted_text.replace("\r\n", "\n")
    blocks = [block.strip() for block in re.split(r"\n\s*\n", normalized) if block.strip()]
    if blocks:
        return blocks

    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    grouped = []
    current = []
    for line in lines:
        current.append(line)
        if len(" ".join(current)) >= 260:
            grouped.append(" ".join(current))
            current = []
    if current:
        grouped.append(" ".join(current))
    return grouped


def _build_fallback_entry(block: str) -> dict | None:
    sentences = _split_sentences(block)
    if not sentences:
        return None

    answer_sentences = sentences[:3]
    answer = " ".join(answer_sentences).strip()
    if len(answer) < 40:
        return None

    topic = _derive_topic(block, sentences[0])
    question = _build_question(topic, sentences[0])
    category = _infer_category(block)
    keywords = _extract_keywords(topic or answer)[:4]
    aliases = [topic] if topic and topic.lower() not in question.lower() else []

    return _normalize_entry({
        "question": question,
        "answer": answer,
        "category": category,
        "keywords": keywords,
        "aliases": aliases,
        "allowed_roles": DEFAULT_ALLOWED_ROLES,
    })


def _derive_topic(block: str, first_sentence: str) -> str:
    heading = block.splitlines()[0].strip(" -:\t")
    if 2 <= len(heading.split()) <= 8 and len(heading) <= 80 and not heading.endswith("."):
        return heading

    if ":" in first_sentence:
        prefix = first_sentence.split(":", 1)[0].strip()
        if 1 < len(prefix.split()) <= 8:
            return prefix

    tokens = _extract_keywords(first_sentence)
    return " ".join(tokens[:4]).strip()


def _build_question(topic: str, first_sentence: str) -> str:
    if first_sentence.endswith("?"):
        return first_sentence.strip()
    if topic:
        if topic.lower().startswith(("how ", "what ", "when ", "where ", "who ")):
            return topic if topic.endswith("?") else f"{topic}?"
        return f"What should employees know about {topic}?"
    return "What information was imported from this PDF?"


def _infer_category(text: str) -> str:
    lowered = text.lower()
    best_category = "General"
    best_score = 0
    for category, keywords in _CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score > best_score:
            best_score = score
            best_category = category
    return best_category


def _split_sentences(text: str) -> list[str]:
    normalized = " ".join(text.split())
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]
    return parts


def _normalize_entries(entries: Any) -> list[dict]:
    if not isinstance(entries, list):
        return []

    normalized = []
    seen = set()
    for item in entries:
        candidate = _normalize_entry(item)
        if not candidate:
            continue
        question_key = candidate["question"].lower()
        if question_key in seen:
            continue
        seen.add(question_key)
        normalized.append(candidate)
    return normalized


def _normalize_entry(item: Any) -> dict | None:
    if not isinstance(item, dict):
        return None

    question = " ".join(str(item.get("question", "")).split()).strip()
    answer = " ".join(str(item.get("answer", "")).split()).strip()
    if not question or not answer:
        return None

    category = " ".join(str(item.get("category", "General")).split()).strip() or "General"
    keywords = _normalize_string_list(item.get("keywords", []))
    aliases = _normalize_string_list(item.get("aliases", []))
    allowed_roles = _normalize_roles(item.get("allowed_roles", DEFAULT_ALLOWED_ROLES))

    if not keywords:
        keywords = _extract_keywords(question)[:4]

    return {
        "question": question,
        "answer": answer,
        "category": category,
        "keywords": keywords,
        "aliases": aliases,
        "allowed_roles": allowed_roles,
    }


def _normalize_text(value: str) -> str:
    return (value or "").replace("\x00", " ").strip()


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        values = []

    normalized = []
    seen = set()
    for item in values:
        text = " ".join(str(item).strip().split())
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(text)
    return normalized


def _normalize_roles(value: Any) -> list[str]:
    normalized = []
    seen = set()
    for role in _normalize_string_list(value):
        lowered = role.lower()
        if lowered not in {"admin", "hr", "intern"} or lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(lowered)
    return normalized or DEFAULT_ALLOWED_ROLES.copy()


def _extract_keywords(text: str) -> list[str]:
    seen = set()
    keywords = []
    for token in _TOKEN_PATTERN.findall((text or "").lower()):
        if token in _STOP_WORDS or token in seen or len(token) < 3:
            continue
        seen.add(token)
        keywords.append(token)
    return keywords
