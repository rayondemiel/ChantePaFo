import asyncio
import hashlib
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from app.auth.dependencies import get_current_user
from app.config import settings
from app.models import User

router = APIRouter(prefix="/audio", tags=["audio"])

# Allowed MIME types for audio uploads.
# WebM/Opus = Chrome, Firefox, Edge. MP4/AAC = Safari fallback.
# The frontend picks the best available via MediaRecorder.isTypeSupported().
_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "audio/webm",
        "audio/mp4",
    }
)

# Max upload size: 5 MB.
_MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _detect_format(content: bytes) -> str | None:
    """Detect audio format from magic bytes. Returns 'webm' or 'mp4' or None."""
    if len(content) < 12:
        return None

    # WebM: starts with EBML header 0x1A45DFA3
    if content[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"

    # MP4/M4A: 'ftyp' box marker at byte offset 4
    if content[4:8] == b"ftyp":
        return "mp4"

    return None


@router.post(
    "/upload",
    responses={
        400: {"description": "Invalid file type or size"},
        401: {"description": "Missing or invalid auth"},
    },
)
async def upload_audio(
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    x_content_sha256: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    # Step 1: check declared content type
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(400, "File type not allowed. Accepted: audio/webm, audio/mp4")

    # Step 2: read and check size
    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(400, f"File too large (max {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB)")

    # Step 3: integrity check — if the client sent a SHA-256, verify it
    actual_hash = hashlib.sha256(content).hexdigest()
    if x_content_sha256 and actual_hash != x_content_sha256.strip().lower():
        raise HTTPException(400, "Integrity check failed: SHA-256 mismatch")

    # Step 4: verify actual content via magic bytes (don't trust the declared type)
    detected = _detect_format(content)
    if detected is None:
        raise HTTPException(400, "File content does not match any allowed audio format")

    # Step 5: cross-check declared type vs detected content
    expected = "webm" if content_type == "audio/webm" else "mp4"
    if detected != expected:
        raise HTTPException(400, "Declared content type does not match file content")

    # Step 6: write with a safe random filename
    filename = f"{uuid.uuid4()}.{detected}"
    upload_dir = os.path.realpath(settings.upload_dir)
    filepath = os.path.realpath(os.path.join(upload_dir, filename))
    if not filepath.startswith(upload_dir + os.sep):
        raise HTTPException(400, "Invalid upload path")

    await asyncio.to_thread(_sync_write, filepath, content)

    # Return the URL + server-computed hash so the client can verify round-trip
    return {"url": f"/uploads/{filename}", "sha256": actual_hash}


def _sync_write(filepath: str, content: bytes) -> None:
    with open(filepath, "wb") as f:
        f.write(content)
