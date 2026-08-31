"""Validation at the boundary: bad input never reaches the agent."""

import pytest
from pydantic import ValidationError

from app.api.schemas import RouteRequest


def test_valid_request_passes() -> None:
    request = RouteRequest(email="jan@example.com", message="Nie dziala mi komputer.")
    assert request.email == "jan@example.com"


def test_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        RouteRequest(email="nie-adres", message="test")


def test_rejects_empty_message() -> None:
    with pytest.raises(ValidationError):
        RouteRequest(email="jan@example.com", message="")


def test_rejects_oversized_message() -> None:
    with pytest.raises(ValidationError):
        RouteRequest(email="jan@example.com", message="a" * 4001)
