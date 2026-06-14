#!/usr/bin/env python3
"""Jednorazowy backfill kursów dla podanego zakresu dat."""

import sys
from datetime import date, timedelta

sys.path.insert(0, "/home/lubapl/hq/kurs-euro")
from pobierz_kursy import czy_dzien_roboczy, pobierz_kurs_nbp, zapisz_csv, WALUTY, PLIK_CSV

START = date(2026, 5, 1)
END   = date(2026, 5, 20)

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
