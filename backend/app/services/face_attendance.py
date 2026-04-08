import base64
import hashlib
import io

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.models.face_profile import FaceProfile

BASE_IMAGE_SIZE = (96, 96)
GLOBAL_FEATURE_SIZE = (24, 24)
CENTER_FEATURE_SIZE = (20, 20)
GRID_SIZE = 6
MATCH_THRESHOLD = 0.965
AMBIGUOUS_MARGIN = 0.015


def _decode_image_bytes(image_payload: str) -> bytes:
    if not image_payload:
        raise ValueError("Image payload is required")

    payload = image_payload.strip()
    if "," in payload and payload.startswith("data:image"):
        payload = payload.split(",", 1)[1]

    try:
        return base64.b64decode(payload, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid base64 image payload") from exc


def _load_image(raw_bytes: bytes) -> np.ndarray:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise ValueError("Pillow is required for image decoding. Install backend dependencies first.") from exc

    try:
        image = Image.open(io.BytesIO(raw_bytes)).convert("L")
        image = ImageOps.exif_transpose(image)
        image = ImageOps.autocontrast(image)
        image = image.resize(BASE_IMAGE_SIZE)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Unsupported image format") from exc

    array = np.asarray(image, dtype=np.float32) / 255.0
    if float(array.std()) < 0.02:
        raise ValueError("Image contains insufficient signal for recognition")
    return array


def _normalize_feature(vector: np.ndarray) -> np.ndarray:
    centered = vector.astype(np.float32) - float(np.mean(vector))
    norm = float(np.linalg.norm(centered))
    if norm == 0:
        raise ValueError("Image contains insufficient signal for recognition")
    return centered / norm


def _pooled_grid(image: np.ndarray, grid_size: int) -> np.ndarray:
    height, width = image.shape
    block_h = height // grid_size
    block_w = width // grid_size
    pooled = []
    for row in range(grid_size):
        for col in range(grid_size):
            block = image[row * block_h:(row + 1) * block_h, col * block_w:(col + 1) * block_w]
            pooled.append(float(block.mean()))
            pooled.append(float(block.std()))
    return np.array(pooled, dtype=np.float32)


def _extract_features(image: np.ndarray) -> np.ndarray:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Pillow is required for image decoding. Install backend dependencies first.") from exc

    pil_image = Image.fromarray(np.uint8(np.clip(image * 255.0, 0, 255)))
    global_view = np.asarray(pil_image.resize(GLOBAL_FEATURE_SIZE), dtype=np.float32) / 255.0

    height, width = image.shape
    crop_h = int(height * 0.62)
    crop_w = int(width * 0.62)
    start_y = (height - crop_h) // 2
    start_x = (width - crop_w) // 2
    center_crop = image[start_y:start_y + crop_h, start_x:start_x + crop_w]
    center_view = np.asarray(
        Image.fromarray(np.uint8(np.clip(center_crop * 255.0, 0, 255))).resize(CENTER_FEATURE_SIZE),
        dtype=np.float32,
    ) / 255.0

    grad_y, grad_x = np.gradient(image)
    grad_mag = np.sqrt((grad_x ** 2) + (grad_y ** 2))
    grad_mag = grad_mag / (float(grad_mag.max()) + 1e-6)

    feature_parts = [
        global_view.reshape(-1),
        center_view.reshape(-1),
        _pooled_grid(image, GRID_SIZE),
        _pooled_grid(grad_mag, GRID_SIZE),
        image.mean(axis=0),
        image.mean(axis=1),
    ]
    return _normalize_feature(np.concatenate(feature_parts))


def build_face_embedding(image_payload: str) -> tuple[np.ndarray, str]:
    raw = _decode_image_bytes(image_payload)
    image = _load_image(raw)
    embedding = _extract_features(image)
    sample_hash = hashlib.sha256(raw).hexdigest()
    return embedding, sample_hash


def _score_embeddings(probe_embedding: np.ndarray, known_embedding: np.ndarray) -> float:
    if probe_embedding.shape != known_embedding.shape:
        return -1.0
    return float(cosine_similarity(probe_embedding.reshape(1, -1), known_embedding.reshape(1, -1))[0][0])


def get_face_profile_for_user(user_id: int) -> FaceProfile | None:
    return FaceProfile.query.filter_by(user_id=user_id).first()


def _match_probe_to_profiles(
    probe_embedding: np.ndarray,
    profiles: list[FaceProfile],
    threshold: float = MATCH_THRESHOLD,
):
    if not profiles:
        return None, 0.0

    scored_profiles = []
    for profile in profiles:
        known = profile.get_embedding()
        score = _score_embeddings(probe_embedding, known)
        if score >= 0:
            scored_profiles.append((profile, score))

    if not scored_profiles:
        return None, 0.0

    scored_profiles.sort(key=lambda item: item[1], reverse=True)
    best_profile, best_score = scored_profiles[0]
    second_best_score = scored_profiles[1][1] if len(scored_profiles) > 1 else -1.0

    if best_score < threshold:
        return None, max(best_score, 0.0)

    # Reject cases where multiple profiles look nearly identical to the probe.
    if second_best_score >= 0 and (best_score - second_best_score) < AMBIGUOUS_MARGIN:
        return None, max(best_score, 0.0)

    return best_profile, best_score


def match_face(image_payload: str, threshold: float = MATCH_THRESHOLD):
    probe_embedding, _ = build_face_embedding(image_payload)
    profiles = FaceProfile.query.all()
    return _match_probe_to_profiles(probe_embedding, profiles, threshold=threshold)


def match_face_for_user(user_id: int, image_payload: str, threshold: float = MATCH_THRESHOLD):
    probe_embedding, _ = build_face_embedding(image_payload)
    profile = get_face_profile_for_user(user_id)
    if not profile:
        return None, 0.0
    return _match_probe_to_profiles(probe_embedding, [profile], threshold=threshold)
