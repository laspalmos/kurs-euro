# Kursy walut NBP

<!-- streak -->
**Streak:** 1 dzień roboczy z rzędu
<!-- /streak -->

Skrypt pobierający dzienne kursy USD, EUR i GBP z [API Narodowego Banku Polskiego](https://api.nbp.pl) zgodnie z regułami rozliczeń księgowych.

## Zasada działania

Według polskich przepisów rachunkowych do przeliczenia walut stosuje się kurs z **ostatniego dnia roboczego poprzedzającego dzień transakcji**. Skrypt automatycznie wyznacza tę datę, uwzględniając:

- weekendy (sobota, niedziela)
- polskie święta ustawowe ([tekst jednolity ustawy o dniach wolnych od pracy, Dz.U. 2025 poz. 296](http://dziennikustaw.gov.pl/D2025000029601.pdf))
- święta ruchome: Wielkanoc, Poniedziałek Wielkanocny, Zielone Świątki, Boże Ciało
- zastępczy dzień wolny, gdy święto stałe wypada w niedzielę
- Wigilia Bożego Narodzenia (24 grudnia) jako dzień wolny od 1 lutego 2025 r.

## Wymagania

- Python 3.10+
- dostęp do internetu (api.nbp.pl)

## Użycie

```bash
python3 pobierz_kursy.py
```

Przykładowy wynik:

```
Data rozliczenia: 2026-05-20, szukam kursów z: 2026-05-19
  USD: 3.6525 (kurs z 2026-05-19)
  EUR: 4.2489 (kurs z 2026-05-19)
  GBP: 4.8745 (kurs z 2026-05-19)

Zapisano 3 kursów do pliku: kursy_nbp.csv
```

## Plik wyjściowy

Kursy zapisywane są do pliku `kursy_nbp.csv` (dopisywanie, bez duplikatów):

```
data_kursu,waluta,kurs_mid
2026-05-19,EUR,4.2489
2026-05-19,GBP,4.8745
2026-05-19,USD,3.6525
```

| Kolumna | Opis |
|---|---|
| `data_kursu` | Data publikacji kursu przez NBP |
| `waluta` | Kod waluty (USD / EUR / GBP) |
| `kurs_mid` | Kurs średni (tabela A NBP) |

## Automatyczne uruchamianie (cron)

Skrypt skonfigurowany jest do uruchamiania każdego dnia roboczego o 8:00:

```
0 8 * * 1-5 /usr/bin/python3 /home/username/kurs-euro/pobierz_kursy.py >> /home/username/kurs-euro/kursy_nbp.log 2>&1
```

Logi zapisywane są do `kursy_nbp.log` (pomijane przez git).
