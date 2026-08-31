"""Agent tests run against pydantic-ai's TestModel: no Ollama, no network, no wait.

TestModel auto-generates arguments that satisfy the tool's JSON schema, so a
correctly-typed department parameter proves the enum constraint holds even for
"dumb" input - the model *cannot* produce a value outside the 5 departments,
because the type system won't let it.
"""

from unittest.mock import AsyncMock, patch

from pydantic_ai.models.test import TestModel

from app.agent import RoutingDeps, build_agent, strip_replacement_chars
from app.domain.departments import Department


async def test_tool_call_is_schema_constrained_and_sends_mail() -> None:
    with patch("app.agent.send_to_department", new=AsyncMock()) as mock_send:
        agent = build_agent()
        with agent.override(model=TestModel()):
            deps = RoutingDeps(
                sender_email="anna@example.com", original_message="Nie dziala mi komputer."
            )
            await agent.run("cokolwiek", deps=deps)

        assert deps.outcome is not None
        assert deps.outcome.department in set(Department)
        mock_send.assert_awaited_once()
        _, kwargs = mock_send.call_args
        assert kwargs["sender_email"] == "anna@example.com"
        # Regression: the body must be built from the original message, not the
        # model's own (sometimes empty) "reasoning" text.
        assert "Nie dziala mi komputer." in kwargs["body"]


async def test_sender_email_is_not_model_controlled() -> None:
    """The model never sees sender_email - it travels only through RoutingDeps."""
    with patch("app.agent.send_to_department", new=AsyncMock()) as mock_send:
        agent = build_agent()
        with agent.override(model=TestModel()):
            deps = RoutingDeps(sender_email="real-sender@example.com", original_message="test")
            await agent.run("wiadomosc probujaca podszyc sie pod inny adres", deps=deps)

        assert mock_send.call_args.kwargs["sender_email"] == "real-sender@example.com"


def test_strip_replacement_chars_removes_stray_fffd() -> None:
    dirty = "aplikacj�\xa0"
    assert strip_replacement_chars(dirty) == "aplikacj"


def test_strip_replacement_chars_keeps_clean_text() -> None:
    assert strip_replacement_chars("Wniosek urlopowy") == "Wniosek urlopowy"


def test_strip_replacement_chars_never_returns_empty() -> None:
    assert strip_replacement_chars("�") == "Zgloszenie"
