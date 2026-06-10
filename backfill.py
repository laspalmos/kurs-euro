#!/usr/bin/env python3
"""Jednorazowy backfill kursów dla podanego zakresu dat.

Użycie:
    python3 backfill.py RRRR-MM-DD RRRR-MM-DD
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pobierz_kursy import czy_dzien_roboczy, pobierz_kurs_nbp, zapisz_csv, WALUTY, PLIK_CSV


def parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        print(f"Błędna data: {s!r} — oczekiwany format RRRR-MM-DD", file=sys.stderr)
        sys.exit(1)


if len(sys.argv) != 3:
    print(f"Użycie: {sys.argv[0]} DATA-OD DATA-DO  (np. 2026-05-01 2026-05-20)", file=sys.stderr)
    sys.exit(1)

START = parse_date(sys.argv[1])
END   = parse_date(sys.argv[2])

if START > END:
    print("DATA-OD nie może być późniejsza niż DATA-DO", file=sys.stderr)
    sys.exit(1)

dzien = START
while dzien <= END:
    if czy_dzien_roboczy(dzien):
        wiersze = []
        for waluta in WALUTY:
            kurs = pobierz_kurs_nbp(waluta, dzien)
            if kurs is not None:
                wiersze.append({
                    "data_kursu": dzien.isoformat(),
                    "waluta": waluta,
                    "kurs_mid": f"{kurs:.4f}",
                })
        if wiersze:
            zapisanych = zapisz_csv(wiersze, PLIK_CSV)
            status = f"zapisano {zapisanych} kursów" if zapisanych else "już istnieje"
            print(f"  {dzien}: {status}")
        else:
            print(f"  {dzien}: brak danych z NBP")
    dzien += timedelta(days=1)

print("\nGotowe.")
