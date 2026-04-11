"""Tests for the /metrics endpoint: auth, HTTP middleware recording, and room counter."""

import httpx

_METRICS_USER = "metrics"
_METRICS_PASS = "test-metrics-password-long-enough-for-tests"
_VALID_AUTH = httpx.BasicAuth(_METRICS_USER, _METRICS_PASS)


async def test_metrics_requires_auth(client):
    resp = await client.get("/metrics")
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers
    assert resp.headers["WWW-Authenticate"] == "Basic"


async def test_metrics_rejects_wrong_password(client):
    resp = await client.get("/metrics", auth=httpx.BasicAuth(_METRICS_USER, "wrongpassword!!!"))
    assert resp.status_code == 401


async def test_metrics_rejects_wrong_username(client):
    resp = await client.get("/metrics", auth=httpx.BasicAuth("baduser", _METRICS_PASS))
    assert resp.status_code == 401


async def test_metrics_returns_prometheus_format(client):
    resp = await client.get("/metrics", auth=_VALID_AUTH)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    body = resp.text
    # Standard default collectors included by prometheus-client
    assert "python_info" in body or "process_start_time_seconds" in body
    # At least one chantepafo_* stub metric must appear
    assert "chantepafo_" in body


async def test_http_middleware_records_request_count(client):
    # Hit a real route so the middleware records it.
    await client.post(
        "/auth/register",
        json={
            "username": "metricsuser",
            "email": "metricsuser@example.com",
            "password": "password1",
        },
    )
    resp = await client.get("/metrics", auth=_VALID_AUTH)
    assert resp.status_code == 200
    body = resp.text
    # The middleware must have recorded this POST with method label "POST"
    assert "chantepafo_http_requests_total{" in body
    assert 'method="POST"' in body
    # The route template (not the raw URL) must appear in a label
    assert 'path="' in body


async def test_health_endpoint_not_instrumented(client):
    # Hit /health several times — should NOT appear in metrics.
    for _ in range(3):
        await client.get("/health")
    resp = await client.get("/metrics", auth=_VALID_AUTH)
    assert resp.status_code == 200
    body = resp.text
    # No series should have path="/health"
    assert 'path="/health"' not in body


async def test_rooms_created_counter_increments(authed_client):
    # Read counter value before creating a room.
    before_resp = await authed_client.get("/metrics", auth=_VALID_AUTH)
    assert before_resp.status_code == 200

    def _parse_counter(text: str) -> float | None:
        """Parse chantepafo_rooms_created_total value from Prometheus exposition text."""
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("chantepafo_rooms_created_total") and not line.startswith("#"):
                parts = line.rsplit(" ", 1)
                if len(parts) == 2:
                    try:
                        return float(parts[1])
                    except ValueError:
                        return None
        return None

    before_value = _parse_counter(before_resp.text) or 0.0

    # Create a room via the REST API.
    create_resp = await authed_client.post("/rooms", json={"host_name": "alice"})
    assert create_resp.status_code == 201

    # Re-read metrics.
    after_resp = await authed_client.get("/metrics", auth=_VALID_AUTH)
    assert after_resp.status_code == 200
    after_value = _parse_counter(after_resp.text)

    assert after_value is not None
    assert after_value > before_value
