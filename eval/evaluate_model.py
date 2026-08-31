"""E7: measure accuracy and latency of the currently-running model through the
REAL API endpoint - not the raw Ollama spike from E1.5. This exercises the actual
production system prompt, ToolOutput agent, and sanitization, so the numbers in
README describe what a reviewer actually gets, not an isolated approximation.

Usage (stack already running via `docker compose up -d`):
    python eval/evaluate_model.py
"""

import statistics
import time

import httpx

from dataset import CASES

API_URL = "http://localhost:8000/api/v1/route"


def main() -> None:
    hits = 0
    fallbacks = 0
    durations: list[float] = []
    misses: list[tuple[str, str, str]] = []

    for message, expected in CASES:
        started = time.perf_counter()
        response = httpx.post(
            API_URL,
            json={"email": "eval@example.com", "message": message},
            timeout=120.0,
        )
        elapsed = time.perf_counter() - started
        durations.append(elapsed)

        body = response.json()
        got = body["department"]
        if body["used_fallback"]:
            fallbacks += 1
        ok = got == expected
        hits += ok
        if not ok:
            misses.append((message, expected, got))

        verdict = "ok" if ok else f"ZLE (chcialem {expected})"
        print(f"  {message[:50]:<50} -> {got:<16} {verdict:<22} {elapsed:5.1f}s")

    total = len(CASES)
    print()
    print(f"Trafnosc: {hits}/{total} ({100 * hits / total:.0f}%)")
    print(f"Fallback uzyty: {fallbacks}/{total}")
    print(f"Czas: mediana {statistics.median(durations):.1f}s, "
          f"srednia {statistics.mean(durations):.1f}s, "
          f"max {max(durations):.1f}s")
    if misses:
        print("\nBledy:")
        for message, expected, got in misses:
            print(f"  '{message}' -> {got} (oczekiwano {expected})")


if __name__ == "__main__":
    main()
