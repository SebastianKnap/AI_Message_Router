"""departments.py is the single source of truth - these tests pin that contract."""

from app.domain.departments import DEPARTMENT_EMAILS, Department, email_for, taxonomy_for_prompt

REQUIRED_ADDRESSES = {
    "human-resources@example.com",
    "help-desk@example.com",
    "it@example.com",
    "kadry@example.com",
    "other@example.com",
}


def test_addresses_match_task_requirements() -> None:
    """The task lists 5 exact addresses - this must never silently drift."""
    assert set(DEPARTMENT_EMAILS.values()) == REQUIRED_ADDRESSES


def test_email_for_every_department() -> None:
    for department in Department:
        assert email_for(department) == DEPARTMENT_EMAILS[department]


def test_taxonomy_prompt_mentions_every_department() -> None:
    prompt = taxonomy_for_prompt()
    for department in Department:
        assert department.value in prompt
