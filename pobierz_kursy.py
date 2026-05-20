#!/usr/bin/env python3
"""
Pobiera kursy USD, EUR, GBP z NBP z poprzedniego dnia roboczego
(zgodnie z regułami rozliczeń księgowych) i zapisuje do pliku CSV.
"""

import csv
import sys
from datetime import date, timedelta
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
import json
import os

WALUTY = ["USD", "EUR", "GBP"]
NBP_URL = "https://api.nbp.pl/api/exchangerates/rates/a/{kod}/{data}/?format=json"

_KATALOG = os.path.dirname(os.path.abspath(__file__))
PLIK_CSV = os.path.join(_KATALOG, "kursy_nbp.csv")
PLIK_LOG = os.path.join(_KATALOG, "kursy_nbp.log")


def wielkanoc(rok: int) -> date:
    """Algorytm Meeusa/Jonesa/Butchera wyznaczający Niedzielę Wielkanocną."""
    a = rok % 19
    b, c = divmod(rok, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    miesiac, dzien = divmod(h + l - 7 * m + 114, 31)
    return date(rok, miesiac, dzien + 1)


def swieta_polskie(rok: int) -> set[date]:
    """
    Zwraca zbiór polskich dni świątecznych dla danego roku (art. 1 ustawy z 18.01.1951).

    Dla stałych świąt wypadających w niedzielę dodaje zastępczy dzień wolny
    w następny poniedziałek — reguła stosowana w rozliczeniach księgowych,
    by nie utracić należnego dnia wolnego.
    Święta ruchome (Wielkanoc, Zielone Świątki) nie podlegają tej regule,
    bo Poniedziałek Wielkanocny jest już ustawowo wolny, a dla Zielonych Świątek
    brak przepisu o zastępstwie.
    """
    w = wielkanoc(rok)

    stale = {
        date(rok, 1, 1),   # Nowy Rok
        date(rok, 1, 6),   # Trzech Króli (od 2011)
        date(rok, 5, 1),   # Święto Pracy
        date(rok, 5, 3),   # Konstytucja 3 Maja (od 1990)
        date(rok, 8, 15),  # Wniebowzięcie NMP
        date(rok, 11, 1),  # Wszystkich Świętych
        date(rok, 11, 11), # Święto Niepodległości (od 1989)
        date(rok, 12, 25), # Boże Narodzenie
        date(rok, 12, 26), # Drugi dzień Bożego Narodzenia
    }
    # Wigilia dodana ustawą z 6.12.2024 (Dz.U. 2024 poz. 1965), obowiązuje od 1.02.2025
    if rok >= 2025:
        stale.add(date(rok, 12, 24))

    ruchome = {
        w,                          # Niedziela Wielkanocna (zawsze nd.)
        w + timedelta(days=1),      # Poniedziałek Wielkanocny
        w + timedelta(days=49),     # Zielone Świątki (zawsze nd.)
        w + timedelta(days=60),     # Boże Ciało (zawsze czwartek)
    }

    # Gdy stałe święto wypada w niedzielę → następny poniedziałek jest zastępczym dniem wolnym.
    # Gdy wypada w sobotę → piątek poprzedzający pozostaje dniem roboczym (brak przepisu
    # o przenoszeniu wolnego z soboty; NBP publikuje tabele w piątek normalnie).
    zastepstwa = {
        s + timedelta(days=1)
        for s in stale
        if s.weekday() == 6  # niedziela
    }

    return stale | ruchome | zastepstwa


def czy_dzien_roboczy(dzien: date) -> bool:
    if dzien.weekday() >= 5:
        return False
    return dzien not in swieta_polskie(dzien.year)


def poprzedni_dzien_roboczy(dzien: date) -> date:
    """Zwraca ostatni dzień roboczy przed podanym dniem (reguła księgowa, z uwzględnieniem świąt)."""
    dzien -= timedelta(days=1)
    while not czy_dzien_roboczy(dzien):
        dzien -= timedelta(days=1)
    return dzien


def pobierz_kurs_nbp(kod_waluty: str, data: date) -> float | None:
    """Pobiera kurs waluty z API NBP dla podanej daty."""
    url = NBP_URL.format(kod=kod_waluty.lower(), data=data.isoformat())
    try:
        with urlopen(url, timeout=10) as resp:
            dane = json.loads(resp.read().decode())
            return dane["rates"][0]["mid"]
    except HTTPError as e:
        if e.code == 404:
            # NBP nie opublikował kursu dla tej daty (święto) — cofnij o jeden dzień roboczy
            return None
        print(f"Błąd HTTP {e.code} dla {kod_waluty}: {e}", file=sys.stderr)
        return None
    except URLError as e:
        print(f"Błąd połączenia: {e}", file=sys.stderr)
        return None


def znajdz_kurs(kod_waluty: str, data_startowa: date, max_prob: int = 5) -> tuple[date, float] | tuple[None, None]:
    """
    Szuka kursu cofając się do poprzednich dni roboczych (obsługa świąt).
    Zwraca parę (data_kursu, kurs) lub (None, None) jeśli nie znaleziono.
    """
    data = data_startowa
    for _ in range(max_prob):
        kurs = pobierz_kurs_nbp(kod_waluty, data)
        if kurs is not None:
            return data, kurs
        data = poprzedni_dzien_roboczy(data)
    return None, None


def oblicz_streak(plik: str) -> int:
    """
    Zwraca liczbę kolejnych dni roboczych z rzędu, dla których zapisano kursy
    wszystkich walut — licząc wstecz od ostatniej daty w pliku.
    """
    if not os.path.isfile(plik):
        return 0
    with open(plik, newline="", encoding="utf-8") as f:
        wiersze = list(csv.DictReader(f))
    if not wiersze:
        return 0

    # Zbierz daty, dla których zapisano komplet walut
    from collections import Counter
    liczba_walut = len(WALUTY)
    licznik = Counter(w["data_kursu"] for w in wiersze)
    daty_kompletne = {date.fromisoformat(d) for d, n in licznik.items() if n >= liczba_walut}

    if not daty_kompletne:
        return 0

    dzien = max(daty_kompletne)
    streak = 0
    while dzien in daty_kompletne:
        streak += 1
        dzien = poprzedni_dzien_roboczy(dzien)
    return streak


def wczytaj_istniejace(plik: str) -> set[tuple[str, str]]:
    """Zwraca zbiór par (data_kursu, waluta) już zapisanych w pliku."""
    if not os.path.isfile(plik):
        return set()
    with open(plik, newline="", encoding="utf-8") as f:
        return {(r["data_kursu"], r["waluta"]) for r in csv.DictReader(f)}


def zapisz_csv(wiersze: list[dict], plik: str) -> int:
    """Dopisuje tylko wiersze nieobecne w pliku. Zwraca liczbę faktycznie zapisanych."""
    istniejace = wczytaj_istniejace(plik)
    nowe = [w for w in wiersze if (w["data_kursu"], w["waluta"]) not in istniejace]
    if not nowe:
        return 0
    plik_istnieje = os.path.isfile(plik)
    with open(plik, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["data_kursu", "waluta", "kurs_mid"])
        if not plik_istnieje:
            writer.writeheader()
        writer.writerows(nowe)
    return len(nowe)


def main() -> None:
    dzisiaj = date.today()
    data_bazowa = poprzedni_dzien_roboczy(dzisiaj)

    print(f"Data rozliczenia: {dzisiaj}, szukam kursów z: {data_bazowa}")

    wiersze = []
    for waluta in WALUTY:
        data_kursu, kurs = znajdz_kurs(waluta, data_bazowa)
        if kurs is None:
            print(f"  {waluta}: brak danych (sprawdź połączenie z NBP)", file=sys.stderr)
            continue
        wiersze.append({
            "data_kursu": data_kursu.isoformat(),
            "waluta": waluta,
            "kurs_mid": f"{kurs:.4f}",
        })
        print(f"  {waluta}: {kurs:.4f} (kurs z {data_kursu})")

    if not wiersze:
        print("Nie pobrano żadnych kursów.", file=sys.stderr)
        sys.exit(1)

    zapisanych = zapisz_csv(wiersze, PLIK_CSV)
    if zapisanych:
        print(f"\nZapisano {zapisanych} kursów do pliku: {PLIK_CSV}")
    else:
        print(f"\nBrak nowych danych — kursy już istnieją w pliku: {PLIK_CSV}")

    streak = oblicz_streak(PLIK_CSV)
    print(f"Streak: {streak} {'dzień roboczy' if streak == 1 else 'dni roboczych' if 2 <= streak <= 4 else 'dni roboczych'} z rzędu")


if __name__ == "__main__":
    main()
