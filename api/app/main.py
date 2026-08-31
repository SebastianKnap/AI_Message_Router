"""FastAPI application.

Swagger lives under /api/v1/docs because the task requires that exact path.
"""

import logging
import time
import uuid

import httpx
from aiosmtplib.errors import SMTPException
from fastapi import FastAPI, HTTPException, Request
from pydantic_ai.exceptions import ModelAPIError, UnexpectedModelBehavior
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.agent import RoutingDeps, get_agent
from app.api.schemas import RouteRequest, RouteResponse
from app.config import get_settings
from app.domain.departments import FALLBACK_DEPARTMENT, email_for
from app.logging_config import configure_logging
from app.services.mailer import send_to_department

configure_logging(get_settings().log_level)
logger = logging.getLogger("app.routing")

app = FastAPI(
    title="AI Message Router",
    description="Routes incoming messages to the right department using a local LLM agent.",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    redoc_url=None,
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Every request gets an id: propagated from the caller if present, otherwise
    generated. Returned in the response header and threaded through logs, so one
    request's whole story can be grepped out of `docker compose logs api`.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIdMiddleware)


def _unavailable(request_id: str, service: str, exc: Exception) -> HTTPException:
    """A dependency (Ollama, Mailpit) didn't respond - always a 503, never a 500.
    The caller should retry; it isn't their fault and there's nothing to fix client-side.
    """
    logger.error(f"{service}_unreachable", extra={"request_id": request_id, "error": str(exc)})
    return HTTPException(status_code=503, detail=f"{service.capitalize()} unreachable: {exc}")


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    """Liveness: the process is running. Says nothing about Ollama or SMTP."""
    return {"status": "ok"}


@app.get("/ready", tags=["ops"])
async def ready() -> dict[str, str]:
    """Readiness: is Ollama actually reachable right now.

    Separate from /health on purpose - the process can be alive while the model
    engine is still starting or unreachable, and a caller needs to know the
    difference.
    """
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Ollama unreachable: {exc}") from exc
    return {"status": "ready"}


@app.post("/api/v1/route", tags=["routing"])
async def route_message(request: RouteRequest, http_request: Request) -> RouteResponse:
    """Route a message to a department. The agent sends the email itself via tool calling.

    Three distinct failure modes, handled differently:
    - Ollama unreachable/erroring (ModelAPIError) -> 503, the caller should retry.
    - Mailpit/SMTP unreachable (SMTPException, raised inside the tool call and
      propagated straight through agent.run()) -> 503, same reasoning.
    - Model never produces a valid tool call (UnexpectedModelBehavior, retries
      exhausted) -> not the caller's fault, so we fall back to `other@` ourselves
      and still answer 200 with `used_fallback=True`.
    """
    request_id = http_request.state.request_id
    started = time.perf_counter()
    deps = RoutingDeps(sender_email=request.email, original_message=request.message)

    try:
        agent_started = time.perf_counter()
        result = await get_agent().run(request.message, deps=deps)
        agent_seconds = time.perf_counter() - agent_started
    except ModelAPIError as exc:
        raise _unavailable(request_id, "ollama", exc) from exc
    except SMTPException as exc:
        # Raised inside the send_email tool, propagates straight through agent.run() -
        # pydantic-ai does not catch or wrap arbitrary tool exceptions.
        raise _unavailable(request_id, "mailpit", exc) from exc
    except UnexpectedModelBehavior:
        result = None
        agent_seconds = time.perf_counter() - agent_started

    if deps.outcome is None:
        try:
            await send_to_department(
                department=FALLBACK_DEPARTMENT,
                subject="Nierozpoznane zgloszenie",
                body=request.message,
                sender_email=request.email,
            )
        except SMTPException as exc:
            raise _unavailable(request_id, "mailpit", exc) from exc
        logger.info(
            "routed",
            extra={
                "request_id": request_id,
                "department": FALLBACK_DEPARTMENT.value,
                "used_fallback": True,
                "total_seconds": round(time.perf_counter() - started, 2),
                "agent_seconds": round(agent_seconds, 2),
            },
        )
        return RouteResponse(
            department=FALLBACK_DEPARTMENT,
            department_email=email_for(FALLBACK_DEPARTMENT),
            reasoning="Model nie wywolal narzedzia poprawnie - zastosowano fallback.",
            used_fallback=True,
        )

    usage = result.usage if result else None
    logger.info(
        "routed",
        extra={
            "request_id": request_id,
            "department": deps.outcome.department.value,
            "used_fallback": False,
            "total_seconds": round(time.perf_counter() - started, 2),
            "agent_seconds": round(agent_seconds, 2),
            "input_tokens": usage.input_tokens if usage else None,
            "output_tokens": usage.output_tokens if usage else None,
        },
    )
    return RouteResponse(
        department=deps.outcome.department,
        department_email=email_for(deps.outcome.department),
        reasoning=(
            f"Agent wybral dzial na podstawie tresci wiadomosci "
            f"(temat: {deps.outcome.subject})."
        ),
        used_fallback=False,
    )
