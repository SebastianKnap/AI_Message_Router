"""Spike: does a small local model reliably call a tool on Polish messages?

Deliberately talks to Ollama's raw HTTP API - no FastAPI, no pydantic-ai. If tool
calling fails here, no amount of framework on top will fix it, and the answer changes
the model choice, the hardware requirements and the timeouts.

Usage (Ollama exposed on localhost:11434):
    python eval/spike_tool_calling.py qwen3:4b llama3.2:3b
"""

import asyncio
import json
import sys
import time

import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"

DEPARTMENTS = ["kadry", "human-resources", "help-desk", "it", "other"]

SYSTEM_PROMPT = """Jestes routerem zgloszen pracowniczych. Przeczytaj wiadomosc i przekaz
ja do wlasciwego dzialu, wywolujac narzedzie send_email. Zawsze wywolaj narzedzie.

Dzialy:
- kadry: sprawy formalne i dokumenty: urlopy, L4, umowy, PIT, lista plac, zaswiadczenia.
- human-resources: sprawy miekkie: rekrutacja, onboarding, szkolenia, oceny, konflikty, benefity.
- help-desk: wsparcie uzytkownika: nie dziala komputer lub drukarka, reset hasla, dostep do aplikacji.
- it: infrastruktura: awarie serwerow, siec, VPN, bezpieczenstwo, uprawnienia systemowe.
- other: zgloszenia niepasujace do powyzszych, niejasne lub spam."""

TOOL = {
    "type": "function",
    "function": {
        "name": "send_email",
        "description": "Przekazuje zgloszenie do wybranego dzialu.",
        "parameters": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "enum": DEPARTMENTS,
                    "description": "Dzial, do ktorego trafia zgloszenie.",
                },
                "subject": {"type": "string", "description": "Krotki temat wiadomosci."},
            },
            "required": ["department", "subject"],
        },
    },
}

# (wiadomosc, oczekiwany dzial)
CASES: list[tuple[str, str]] = [
    ("Nie dziala mi komputer, nie wlacza sie ekran.", "help-desk"),
    ("Chcialbym zglosic urlop na jutro.", "kadry"),
    ("Kiedy dostane PIT-11 za zeszly rok?", "kadry"),
    ("Chcialbym porozmawiac o konflikcie z moim przelozonym.", "human-resources"),
    ("Serwer produkcyjny nie odpowiada, aplikacja zwraca blad 502.", "it"),
    ("Czy mozecie polecic dobra restauracje na obiad?", "other"),
]


async def ask(client: httpx.AsyncClient, model: str, message: str) -> tuple[str | None, float]:
    """Return the department the model picked (or None if it ignored the tool) and elapsed seconds."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        "tools": [TOOL],
        "stream": False,
        "think": False,  # qwen3 reasons out loud by default, which we do not want here
        "options": {"temperature": 0},
    }
    started = time.perf_counter()
    response = await client.post(OLLAMA_URL, json=payload, timeout=300.0)
    response.raise_for_status()
    elapsed = time.perf_counter() - started

    tool_calls = response.json().get("message", {}).get("tool_calls") or []
    if not tool_calls:
        return None, elapsed

    arguments = tool_calls[0]["function"]["arguments"]
    if isinstance(arguments, str):  # some builds return arguments as a JSON string
        arguments = json.loads(arguments)
    return arguments.get("department"), elapsed


async def run_model(model: str) -> None:
    print(f"\n=== {model} ===")
    hits, tool_misses, times = 0, 0, []

    async with httpx.AsyncClient() as client:
        for message, expected in CASES:
            try:
                picked, elapsed = await ask(client, model, message)
            except Exception as exc:  # noqa: BLE001 - a spike reports failures, it does not handle them
                print(f"  BLAD  {message[:45]:<45} {exc}")
                continue

            times.append(elapsed)
            if picked is None:
                tool_misses += 1
                verdict = "BRAK TOOL CALL"
            elif picked == expected:
                hits += 1
                verdict = "ok"
            else:
                verdict = f"zle (chcialem {expected})"

            print(f"  {message[:45]:<45} -> {str(picked):<16} {verdict:<22} {elapsed:5.1f}s")

    total = len(CASES)
    median = sorted(times)[len(times) // 2] if times else 0.0
    print(f"  trafnosc: {hits}/{total} | bez wywolania narzedzia: {tool_misses} | mediana: {median:.1f}s")


async def main() -> None:
    models = sys.argv[1:] or ["qwen3:4b"]
    for model in models:
        await run_model(model)


if __name__ == "__main__":
    asyncio.run(main())
