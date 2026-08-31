"""Department taxonomy: the single source of truth for routing.

The task's address list is deliberately ambiguous: `kadry@` and `human-resources@` are
the same department name in Polish and English, and `help-desk@` overlaps with `it@`.
No model can guess the intended split, so it is defined here explicitly and injected
into the prompt, the tool schema and the API documentation from this one place.

Scope descriptions are in Polish because incoming messages are in Polish.
"""

from enum import StrEnum


class Department(StrEnum):
    """Allowed routing targets. The agent picks one of these, never a raw address."""

    KADRY = "kadry"
    HUMAN_RESOURCES = "human-resources"
    HELP_DESK = "help-desk"
    IT = "it"
    OTHER = "other"


#: Used whenever the model fails to pick a valid department.
FALLBACK_DEPARTMENT = Department.OTHER

DEPARTMENT_EMAILS: dict[Department, str] = {
    Department.KADRY: "kadry@example.com",
    Department.HUMAN_RESOURCES: "human-resources@example.com",
    Department.HELP_DESK: "help-desk@example.com",
    Department.IT: "it@example.com",
    Department.OTHER: "other@example.com",
}

DEPARTMENT_SCOPES: dict[Department, str] = {
    Department.KADRY: (
        "Sprawy formalne i dokumenty pracownicze: urlopy i wnioski urlopowe, zwolnienia "
        "lekarskie i L4, umowy, aneksy, PIT i rozliczenia, lista plac i wynagrodzenia, "
        "swiadectwa pracy, zaswiadczenia."
    ),
    Department.HUMAN_RESOURCES: (
        "Sprawy miekkie i relacje w zespole: rekrutacja, onboarding nowych osob, "
        "szkolenia i rozwoj, oceny okresowe, konflikty i skargi, benefity, kultura pracy."
    ),
    Department.HELP_DESK: (
        "Pierwsza linia wsparcia uzytkownika koncowego: nie dziala komputer, laptop, "
        "monitor lub drukarka, reset hasla, problem z zalogowaniem, prosba o dostep do "
        "aplikacji, instalacja programu, wolno dzialajacy sprzet."
    ),
    Department.IT: (
        "Infrastruktura i inzynieria: awarie serwerow i uslug, problemy z siecia i VPN, "
        "incydenty bezpieczenstwa i phishing, wdrozenia i konfiguracja srodowisk, "
        "uprawnienia systemowe, integracje i bazy danych."
    ),
    Department.OTHER: (
        "Zgloszenia, ktore nie pasuja jednoznacznie do zadnego z powyzszych dzialow, "
        "sa niejasne, puste albo wygladaja na spam."
    ),
}


def email_for(department: Department) -> str:
    """Map a department to its address. The model never supplies an address itself."""
    return DEPARTMENT_EMAILS[department]


def taxonomy_for_prompt() -> str:
    """Render the taxonomy as prompt text so the prompt cannot drift from the code."""
    return "\n".join(
        f"- {department.value}: {DEPARTMENT_SCOPES[department]}" for department in Department
    )
