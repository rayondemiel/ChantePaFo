import hashlib
import io

# Minimal valid magic byte headers for format detection
_WEBM_HEADER = b"\x1a\x45\xdf\xa3" + b"\x00" * 8  # EBML header + padding
_MP4_HEADER = b"\x00\x00\x00\x1c" + b"ftyp" + b"isom" + b"\x00" * 8  # ftyp box


async def test_upload_requires_auth(client: object) -> None:
    fake_file = io.BytesIO(_WEBM_HEADER)
    resp = await client.post(  # type: ignore[union-attr]
        "/audio/upload",
        files={"file": ("test.webm", fake_file, "audio/webm")},
    )
    assert resp.status_code == 401


async def test_upload_webm_success(authed_client: object) -> None:
    content = _WEBM_HEADER + b"\x00" * 100
    fake_audio = io.BytesIO(content)
    resp = await authed_client.post(  # type: ignore[union-attr]
        "/audio/upload",
        files={"file": ("recording.webm", fake_audio, "audio/webm")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"].startswith("/uploads/")
    assert data["url"].endswith(".webm")
    assert "sha256" in data


async def test_upload_mp4_success(authed_client: object) -> None:
    content = _MP4_HEADER + b"\x00" * 100
    fake_audio = io.BytesIO(content)
    resp = await authed_client.post(  # type: ignore[union-attr]
        "/audio/upload",
        files={"file": ("recording.mp4", fake_audio, "audio/mp4")},
    )
    assert resp.status_code == 200
    assert resp.json()["url"].endswith(".mp4")


async def test_upload_rejects_bad_content_type(authed_client: object) -> None:
    fake_html = io.BytesIO(b"<script>alert(1)</script>")
    resp = await authed_client.post(  # type: ignore[union-attr]
        "/audio/upload",
        files={"file": ("evil.html", fake_html, "text/html")},
    )
    assert resp.status_code == 400


async def test_upload_rejects_magic_bytes_mismatch(authed_client: object) -> None:
    # Declare audio/webm but send MP4 content
    content = _MP4_HEADER + b"\x00" * 100
    resp = await authed_client.post(  # type: ignore[union-attr]
        "/audio/upload",
        files={"file": ("fake.webm", io.BytesIO(content), "audio/webm")},
    )
    assert resp.status_code == 400


async def test_upload_rejects_non_audio_content(authed_client: object) -> None:
    # Declare audio/webm but send random bytes (no valid magic)
    resp = await authed_client.post(  # type: ignore[union-attr]
        "/audio/upload",
        files={"file": ("fake.webm", io.BytesIO(b"\x00" * 100), "audio/webm")},
    )
    assert resp.status_code == 400


async def test_upload_rejects_oversize(authed_client: object) -> None:
    content = _WEBM_HEADER + b"\x00" * (6 * 1024 * 1024)  # 6 MB > 5 MB limit
    resp = await authed_client.post(  # type: ignore[union-attr]
        "/audio/upload",
        files={"file": ("big.webm", io.BytesIO(content), "audio/webm")},
    )
    assert resp.status_code == 400


async def test_upload_sha256_integrity_pass(authed_client: object) -> None:
    content = _WEBM_HEADER + b"\x00" * 100
    expected_hash = hashlib.sha256(content).hexdigest()
    resp = await authed_client.post(  # type: ignore[union-attr]
        "/audio/upload",
        files={"file": ("test.webm", io.BytesIO(content), "audio/webm")},
        headers={"X-Content-SHA256": expected_hash},
    )
    assert resp.status_code == 200
    assert resp.json()["sha256"] == expected_hash


async def test_upload_sha256_integrity_fail(authed_client: object) -> None:
    content = _WEBM_HEADER + b"\x00" * 100
    resp = await authed_client.post(  # type: ignore[union-attr]
        "/audio/upload",
        files={"file": ("test.webm", io.BytesIO(content), "audio/webm")},
        headers={"X-Content-SHA256": "0000000000000000000000000000000000000000000000000000000000000000"},
    )
    assert resp.status_code == 400
    assert "SHA-256 mismatch" in resp.json()["detail"]


async def test_upload_without_sha256_still_returns_hash(authed_client: object) -> None:
    content = _WEBM_HEADER + b"\x00" * 100
    resp = await authed_client.post(  # type: ignore[union-attr]
        "/audio/upload",
        files={"file": ("test.webm", io.BytesIO(content), "audio/webm")},
    )
    assert resp.status_code == 200
    # Server always returns the hash even if client didn't send one
    server_hash = resp.json()["sha256"]
    assert server_hash == hashlib.sha256(content).hexdigest()
