"""Labeled evaluation set for E7: 25 messages (PL + a few EN), expected department.

Includes deliberately ambiguous cases (help-desk vs it, kadry vs human-resources)
that mirror the real overlap in the task's department list - see departments.py.
"""

CASES: list[tuple[str, str]] = [
    # kadry - formal HR paperwork
    ("Chcialbym zglosic urlop na jutro.", "kadry"),
    ("Kiedy dostane PIT-11 za zeszly rok?", "kadry"),
    ("Prosze o wystawienie zaswiadczenia o zatrudnieniu.", "kadry"),
    ("Chce zlozyc L4 od poniedzialku, mam zwolnienie lekarskie.", "kadry"),
    ("Czy moge dostac kopie mojej umowy o prace?", "kadry"),
    ("Kiedy wyplacana jest premia roczna?", "kadry"),
    # human-resources - soft HR
    ("Chcialbym porozmawiac o konflikcie z moim przelozonym.", "human-resources"),
    ("Interesuje mnie udzial w szkoleniu z zarzadzania projektami.", "human-resources"),
    ("Kiedy odbeda sie moje roczne oceny pracownicze?", "human-resources"),
    ("Chcialbym zglosic kandydata na stanowisko w naszym zespole.", "human-resources"),
    ("Czy firma organizuje program onboardingowy dla nowych osob?", "human-resources"),
    # help-desk - end-user support
    ("Nie dziala mi komputer, nie wlacza sie ekran.", "help-desk"),
    ("Zapomnialem hasla do systemu, prosze o reset.", "help-desk"),
    ("Drukarka na drugim pietrze znowu sie zacina.", "help-desk"),
    ("Nie moge sie zalogowac do poczty firmowej.", "help-desk"),
    ("Potrzebuje dostepu do aplikacji ksiegowej.", "help-desk"),
    # it - infrastructure/engineering
    ("Serwer produkcyjny nie odpowiada, aplikacja zwraca blad 502.", "it"),
    ("Podejrzewam, ze dostalem maila phishingowego z zewnetrznego adresu.", "it"),
    ("Potrzebujemy wdrozyc nowe srodowisko testowe na przyszly tydzien.", "it"),
    ("Baza danych produkcyjna nie odpowiada od 10 minut.", "it"),
    ("Prosze o nadanie uprawnien administratora do repozytorium.", "it"),
    # other - fallback
    ("Czy mozecie polecic dobra restauracje na obiad?", "other"),
    ("Dzien dobry, mam pytanie niezwiazane z praca.", "other"),
    # English
    ("I would like to request a day off tomorrow.", "kadry"),
    ("My laptop screen is not turning on.", "help-desk"),
]
