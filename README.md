# AI Message Router

[![ci](https://github.com/SebastianKnap/AI_Message_Router/actions/workflows/ci.yml/badge.svg)](https://github.com/SebastianKnap/AI_Message_Router/actions/workflows/ci.yml)

PoC mikroserwisu: endpoint HTTP przyjmuje wolny tekst zgłoszenia pracownika, agent AI na
lokalnym modelu (Ollama, w kontenerze) decyduje, do którego działu ono należy, i sam
wysyła maila poprzez wywołanie narzędzia (tool calling) — model nigdy nie widzi
prawdziwego adresu, tylko ograniczoną do pięciu wartości nazwę działu.

## Uruchomienie środowiska

Wymaga Dockera i Docker Compose. Nic więcej — wagi modelu pobierają się automatycznie
przy pierwszym starcie.

```bash
git clone https://github.com/SebastianKnap/AI_Message_Router
cd AI_Message_Router
docker compose up -d
```

Pierwszy start pobiera obraz Ollamy (~3 GB) i wagi `llama3.2:3b` (~2 GB), więc może
potrwać kilka minut. `docker compose ps` pokazuje `api` jako `starting`, dopóki model nie
skończy się pobierać i rozgrzewać; dopiero wtedy staje się `healthy`. Kolejne starty są
natychmiastowe — wagi zostają w nazwanym wolumenie.

- **Swagger UI**: <http://localhost:8000/api/v1/docs>
- **Mailpit** (podgląd każdego wysłanego maila): <http://localhost:8025>

Żeby uruchomić na słabszym komputerze: `cp .env.example .env` i ustaw mniejszy model,
np. `OLLAMA_MODEL=qwen3:1.7b`.

## Decyzje architektoniczne

- **Python + FastAPI** — Swagger pod `/api/v1/docs` generuje się wprost z tych samych
  modeli Pydantic, które walidują dane wejściowe.
- **pydantic-ai, nie LangChain** — zadanie rekomenduje obie. Wybrane po sprawdzeniu obu
  pod kątem realnego wymogu: mały model na CPU, jedno narzędzie, ograniczony argument.
  Typowane argumenty narzędzia (enum wymuszony automatycznie) i `TestModel` do testów
  bez żywego LLM przeważyły.
- **Model wybrany pomiarem, nie deklaracją** — `llama3.2:3b` (domyślny): 21/25 (84%)
  trafności na oznakowanym zbiorze wiadomości PL/EN, mierzone przez działający endpoint.
  `qwen3:4b` odrzucony po pomiarze: ignoruje `think: false` na tej wersji Ollamy (znany,
  otwarty bug), ponad 200s na wiadomość.
- **Mailpit, nie MailHog** — zadanie dopuszcza "podobne narzędzie". MailHog nie ma
  commitów od lutego 2024; Mailpit jest aktywnie rozwijany i ma REST API, wykorzystane w
  teście E2E do programowego sprawdzenia odbiorcy i `Reply-To`.
- **Narzędzie agenta przyjmuje nazwę działu, nigdy adres** — `department` to Python enum
  pięciu wartości. Próba wstrzyknięcia polecenia w treści wiadomości nie ma parametru,
  przez który mogłaby zadziałać. Adres i nagłówek `Reply-To` ustawia wyłącznie aplikacja.
- **Taksonomia działów w jednym pliku** (`domain/departments.py`) — lista adresów z
  zadania jest niejednoznaczna (`kadry@`/`human-resources@` to ta sama nazwa po polsku i
  angielsku, `help-desk@` nakłada się na `it@`). Podział zdefiniowany raz, zasila
  jednocześnie prompt agenta, walidację i dokumentację API.
- **Kontener inicjalizujący** — jednorazowy kontener pobiera i rozgrzewa model, zanim API
  w ogóle może wystartować, więc `docker compose up -d` naprawdę oznacza "gotowe do
  requestów", nie "działa i zaraz zwróci błąd na pierwszym zapytaniu".

## Przykładowe zapytanie

```bash
curl -X POST http://localhost:8000/api/v1/route \
  -H "Content-Type: application/json" \
  -d '{"email": "jan.kowalski@example.com", "message": "Chcialbym zglosic urlop na jutro."}'
```

```json
{
  "department": "kadry",
  "department_email": "kadry@example.com",
  "reasoning": "Agent wybral dzial na podstawie tresci wiadomosci (temat: Wniosek urlopowy).",
  "used_fallback": false
}
```

## Struktura projektu

```text
api/
├── Dockerfile
├── requirements.txt              # wszystkie zaleznosci, produkcyjne + pytest
├── app/
│   ├── main.py                   # aplikacja FastAPI, endpoint routingu, middleware request-id
│   ├── agent.py                  # Agent pydantic-ai, narzedzie send_email, RoutingDeps
│   ├── config.py                 # Settings (tylko zmienne srodowiskowe, brak wczytywania .env w procesie)
│   ├── logging_config.py         # formatter logow JSON ze standardowej biblioteki
│   ├── api/schemas.py            # RouteRequest / RouteResponse
│   ├── domain/departments.py     # jedyne zrodlo prawdy: enum Department + taksonomia
│   └── services/mailer.py        # buduje i wysyla maila przez aiosmtplib
└── tests/
    ├── test_departments.py       # kontrakt taksonomii
    ├── test_schemas.py           # walidacja danych wejsciowych
    ├── test_agent.py             # agent + narzedzie, przez TestModel (bez zywego LLM)
    ├── test_api.py                # endpoint, agent zamockowany (bez zywego LLM)
    └── test_e2e.py                # prawdziwy stos, prawdziwe REST API Mailpita (pomijany, jesli nie dziala)
eval/
├── dataset.py                    # 25 oznakowanych wiadomosci
├── evaluate_model.py             # pomiar trafnosci/czasu przez prawdziwe API
└── spike_tool_calling.py         # pierwotne porownanie modeli, gole API Ollamy
docker-compose.yml                # ollama, ollama-init, mailpit, api
docker-compose.gpu.yml            # opcjonalna nakladka na przyspieszenie NVIDIA
.github/workflows/ci.yml          # instalacja zaleznosci + testy jednostkowe (bez e2e) na kazdy push/PR
```

## Napotkane błędy i ich naprawy

**Nieaktualny `.env` cicho podmieniał wybór modelu.** Docker Compose sam wczytuje `.env`
z katalogu projektu przy podstawianiu zmiennych — bez żadnego opt-inu. Wczesny plik,
sprzed zmiany modelu na `llama3.2:3b`, wciąż miał starą wartość `qwen3:4b`. Każda
przebudowa kontenera dostawała odrzucony model, mimo poprawnych wartości domyślnych
wszędzie indziej. Naprawa: `config.py` przestał w ogóle wczytywać `.env` — w kontenerze
Compose i tak wstrzykuje zmienne bezpośrednio, więc plik był zbędny i szkodliwy zarazem.

**`tools=[...]` kosztowało niepotrzebne 3x na każdym zapytaniu.** Domyślna pętla agenta
pydantic-ai po wywołaniu narzędzia prosi model o drugą, niewykorzystywaną nigdzie
odpowiedź tekstową kończącą rozmowę. Oznaczenie narzędzia jako końcowego wyjścia
(`output_type=ToolOutput(send_email)` zamiast `tools=[send_email]`) kończy przebieg
natychmiast: **43s → 14s** z jednego argumentu konstruktora.

**Treść maila była budowana z tekstu modelu, który wracał pusty.** Ręczne testowanie
ujawniło maila z dosłownie pustą treścią — była budowana z jednozdaniowego uzasadnienia
pisanego przez sam model, które mogło wrócić puste. Naprawa: treść to teraz zawsze
oryginalna wiadomość użytkownika (zwalidowana jako niepusta już na wejściu do API),
uzasadnienie AI dopisywane tylko, gdy faktycznie coś powiedziało.

**Awaria SMTP dawała goły `500` zamiast `503`.** Wysyłka maila dzieje się wewnątrz
wywołania narzędzia agenta; nieobsłużony wyjątek stamtąd przelatywał przez całą pętlę
agenta prosto do domyślnego handlera FastAPI. Znalezione przez celowe zatrzymanie
Mailpita w trakcie działania i sprawdzenie, co się stanie. Naprawa: złapanie wyjątku SMTP
w obu miejscach wysyłki i zmapowanie na ten sam `503`, co awaria Ollamy.
