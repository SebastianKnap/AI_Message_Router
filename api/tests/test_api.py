"""HTTP layer tests: the agent is replaced with a mock, so these never touch Ollama."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from aiosmtplib.errors import SMTPException
from httpx import ASGITransport, AsyncClient
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior

from app.agent import RoutingOutcome
from app.domain.departments import Department
from app.main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_route_rejects_bad_email(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/route", json={"email": "nie-adres", "message": "test"}
    )
    assert response.status_code == 422


async def test_route_success(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_agent = AsyncMock()

    async def fake_run(message: str, deps: object) -> None:  # noqa: ARG001
        deps.outcome = RoutingOutcome(department=Department.KADRY, subject="Urlop")

    fake_agent.run.side_effect = fake_run
    monkeypatch.setattr("app.main.get_agent", lambda: fake_agent)

    response = await client.post(
        "/api/v1/route",
        json={"email": "jan@example.com", "message": "Chcialbym zglosic urlop."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["department"] == "kadry"
    assert body["department_email"] == "kadry@example.com"
    assert body["used_fallback"] is False


async def test_route_falls_back_when_model_misbehaves(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_agent = AsyncMock()
    fake_agent.run.side_effect = UnexpectedModelBehavior("no valid tool call")
    monkeypatch.setattr("app.main.get_agent", lambda: fake_agent)
    monkeypatch.setattr("app.main.send_to_department", AsyncMock())

    response = await client.post(
        "/api/v1/route", json={"email": "jan@example.com", "message": "cos dziwnego"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["department"] == "other"
    assert body["used_fallback"] is True


async def test_route_returns_503_when_ollama_unreachable(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_agent = AsyncMock()
    fake_agent.run.side_effect = ModelAPIError(
        model_name="llama3.2:3b", message="connection refused"
    )
    monkeypatch.setattr("app.main.get_agent", lambda: fake_agent)

    response = await client.post(
        "/api/v1/route", json={"email": "jan@example.com", "message": "test"}
    )
    assert response.status_code == 503


async def test_route_returns_503_when_mailpit_unreachable_during_success(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The SMTP send happens inside the agent's tool call - an SMTP failure there
    propagates straight through agent.run(), same as if Ollama itself had failed."""
    fake_agent = AsyncMock()
    fake_agent.run.side_effect = SMTPException("Error connecting to mailpit on port 1025")
    monkeypatch.setattr("app.main.get_agent", lambda: fake_agent)

    response = await client.post(
        "/api/v1/route", json={"email": "jan@example.com", "message": "test"}
    )
    assert response.status_code == 503


async def test_route_returns_503_when_mailpit_unreachable_during_fallback(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same failure mode, but hit while sending the fallback `other@` mail instead."""
    fake_agent = AsyncMock()
    fake_agent.run.side_effect = UnexpectedModelBehavior("no valid tool call")
    monkeypatch.setattr("app.main.get_agent", lambda: fake_agent)
    monkeypatch.setattr(
        "app.main.send_to_department",
        AsyncMock(side_effect=SMTPException("Error connecting to mailpit on port 1025")),
    )

    response = await client.post(
        "/api/v1/route", json={"email": "jan@example.com", "message": "cos dziwnego"}
    )
    assert response.status_code == 503
