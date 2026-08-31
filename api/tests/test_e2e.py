"""End-to-end: real API, real Ollama, real Mailpit. Requires `docker compose up -d`.

This is the actual acceptance criterion from the task, automated: a message goes
in over HTTP, and a real email with the right recipient and Reply-To comes out
the other side, verified via Mailpit's own REST API.

Skipped automatically (not failed) if the stack isn't running - see README for
how to run these locally. Excluded from CI via the `e2e` marker.
"""

import uuid

import httpx
import pytest

API_URL = "http://localhost:8000"
MAILPIT_URL = "http://localhost:8025"


@pytest.fixture(autouse=True)
def _require_live_stack() -> None:
    try:
        httpx.get(f"{API_URL}/health", timeout=2.0).raise_for_status()
        httpx.get(f"{MAILPIT_URL}/api/v1/messages?limit=1", timeout=2.0).raise_for_status()
    except httpx.HTTPError:
        pytest.skip("live stack not reachable - run `docker compose up -d` first")


@pytest.mark.e2e
def test_message_arrives_with_correct_recipient_and_reply_to() -> None:
    sender = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
    response = httpx.post(
        f"{API_URL}/api/v1/route",
        json={"email": sender, "message": "Chcialbym zglosic urlop na jutro."},
        timeout=60.0,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["department"] == "kadry"

    # Search by the unique sender address (embedded as Reply-To) - it is the only
    # value in this message guaranteed not to collide with other test runs.
    messages = httpx.get(
        f"{MAILPIT_URL}/api/v1/search",
        params={"query": f'"{sender}"'},
        timeout=5.0,
    )
    results = messages.json()["messages"]
    assert len(results) == 1, f"expected exactly one matching message, found {len(results)}"

    detail = httpx.get(f"{MAILPIT_URL}/api/v1/message/{results[0]['ID']}", timeout=5.0).json()
    assert detail["To"][0]["Address"] == "kadry@example.com"
    assert detail["ReplyTo"][0]["Address"] == sender
