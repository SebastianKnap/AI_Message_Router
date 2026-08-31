"""One-off: run the real agent against Ollama on a Polish message. Not a pytest file."""

import asyncio

from app.agent import RoutingDeps, build_agent


async def main() -> None:
    agent = build_agent()
    deps = RoutingDeps(
        sender_email="anna.nowak@example.com",
        original_message="Serwer produkcyjny nie odpowiada, aplikacja zwraca blad 502.",
    )
    result = await agent.run(
        "Serwer produkcyjny nie odpowiada, aplikacja zwraca blad 502.", deps=deps
    )
    print("Odpowiedz modelu:", result.output)
    print("Outcome:", deps.outcome)
    if deps.outcome:
        print("Subject repr:", repr(deps.outcome.subject))
        print("Subject bytes:", deps.outcome.subject.encode("utf-8"))


asyncio.run(main())
