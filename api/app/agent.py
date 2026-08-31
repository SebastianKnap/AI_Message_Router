"""The routing agent: decides a department, sends the email itself via tool calling.

The task requires the AGENT to trigger the send through function calling, not just
report a decision that application code acts on afterwards - so the tool here really
does call the mailer. The sender's email never reaches the model: it travels through
`RoutingDeps`, outside the tool's JSON schema, so the model has no channel to change it.
"""

from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent, RunContext, ToolOutput
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from app.config import get_settings
from app.domain.departments import Department, taxonomy_for_prompt
from app.services.mailer import send_to_department

SYSTEM_PROMPT = f"""Jestes routerem zgloszen pracowniczych. Przeczytaj wiadomosc
i wywolaj narzedzie send_email dokladnie raz, wybierajac jeden z dzialow:

{taxonomy_for_prompt()}

Zawsze wywoluj narzedzie - nawet gdy wiadomosc jest niejasna, wybierz wtedy 'other'."""


@dataclass
class RoutingOutcome:
    department: Department
    subject: str


@dataclass
class RoutingDeps:
    sender_email: str
    # The guaranteed-non-empty source of truth for the email body - never the
    # model's own "reasoning" text, which can come back blank or too thin for a
    # human on the receiving end to act on. See strip_replacement_chars for why
    # free-text model output is never trusted as-is at a system boundary.
    original_message: str
    outcome: RoutingOutcome | None = None


def strip_replacement_chars(text: str) -> str:
    """On rare longer generations the model truncates mid-character, leaving a
    stray U+FFFD. Strip it rather than mail out visibly broken (or blank) text -
    the model has also been observed returning an empty string outright, not
    just a corrupted one, so an empty result after stripping falls back too."""
    return text.replace("�", "").strip() or "Zgloszenie"


async def send_email(
    ctx: RunContext[RoutingDeps],
    department: Department,
    subject: str,
    reasoning: str,
) -> str:
    """Wysyla zgloszenie do wybranego dzialu.

    Args:
        department: dzial, do ktorego nalezy przekazac zgloszenie.
        subject: krotki temat wiadomosci.
        reasoning: jednozdaniowe uzasadnienie wyboru dzialu.
    """
    clean_subject = strip_replacement_chars(subject)
    # Always disclose that routing was automatic - a human misrouted by the AI
    # should know it wasn't a colleague's mistake. Only append the model's own
    # reasoning when it actually said something; an empty/stripped reasoning
    # would otherwise read as a broken template ("...: brak uzasadnienia").
    clean_reasoning = reasoning.replace("�", "").strip()
    note = "Zgloszenie zostalo przekierowane automatycznie przez system AI."
    if clean_reasoning:
        note += f" Uzasadnienie: {clean_reasoning}"
    body = f"{ctx.deps.original_message}\n\n---\n{note}"

    await send_to_department(
        department=department,
        subject=clean_subject,
        body=body,
        sender_email=ctx.deps.sender_email,
    )
    ctx.deps.outcome = RoutingOutcome(department=department, subject=clean_subject)
    return f"Wyslano do {department.value}."


def build_agent() -> Agent[RoutingDeps, str]:
    settings = get_settings()
    model = OpenAIChatModel(
        settings.ollama_model,
        provider=OllamaProvider(base_url=settings.ollama_openai_url),
    )
    return Agent(
        model,
        deps_type=RoutingDeps,
        system_prompt=SYSTEM_PROMPT,
        # ToolOutput, not tools=[...]: calling send_email ENDS the run immediately with
        # its return value as the result. Plain tools=[...] would make the model do a
        # second generation round to produce a closing chat reply we never use - that
        # extra round trip was most of the 43s measured in the first real test.
        output_type=ToolOutput(send_email),
        retries=2,
        model_settings={"temperature": 0.0, "timeout": settings.llm_timeout_seconds},
    )


@lru_cache
def get_agent() -> Agent[RoutingDeps, str]:
    """Cached: reuse one agent/HTTP client across requests instead of rebuilding per call."""
    return build_agent()
