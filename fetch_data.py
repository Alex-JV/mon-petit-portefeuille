#!/usr/bin/env python3
"""
Script one-shot : fetch tous les résultats et écrit data.py.

Usage :
    python3 fetch_data.py

Fait 13 pseudos × 4 bookmakers × mise 1€ = 52 requêtes, ~15 secondes.
Génère data.py que app.py importe pour un rendu instantané.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

API_URL = "https://mes-profits-pronos.vercel.app/api/calculate"
BOOKMAKERS = ["best", "betclic", "unibet", "winamax"]
DELAY_SEC = 0.15

LEAGUE = [
    ("Adedadz",          "Adélaïde",  1,  4811),
    ("AlexRougier",      "Alexandre", 2,  4629),
    ("Sir_Chatonne",     "Alexandre", 3,  4329),
    ("K-Dab",            "Karim",     4,  4324),
    ("M9rgan",           "Morgan",    5,  4079),
    ("GOAT#UEBF1WEA",    "Gilian",    6,  3922),
    ("Foz",              "Clément",   7,  3920),
    ("CedreLePoulpe",    "Cedric",    8,  3805),
    ("Merwi",            "Marie",     9,  3713),
    ("Jean-Porc-Jajo",   "Jade",      10, 3711),
    ("HugBagr",          "Hug",       11, 3650),
    ("BRANDAO_DOBRAZIL", "Samba",     12, 3394),
    ("Pascalou_",        "Thomas",    13, 1556),
]


def fetch(username: str, bookmaker: str):
    body = json.dumps({"username": username, "bookmaker": bookmaker, "stake": 1}).encode()
    req = urllib.request.Request(
        API_URL, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    data = {bm: {} for bm in BOOKMAKERS}
    total = len(LEAGUE) * len(BOOKMAKERS)
    done = 0
    failed = []

    print(f"Fetching {total} combinaisons ({len(LEAGUE)} pseudos × {len(BOOKMAKERS)} bookmakers)...")
    for username, *_ in LEAGUE:
        for bm in BOOKMAKERS:
            done += 1
            print(f"  [{done:2}/{total}] {username:20s} · {bm:8s} ...", end=" ", flush=True)
            try:
                d = fetch(username, bm)
                # On ne garde que les champs utiles pour alléger data.py
                data[bm][username] = {
                    "profit": d["profit"],
                    "roi": d["roi"],
                    "wins": d["wins"],
                    "bets": d["bets"],
                    "winRate": d["winRate"],
                    "totalStake": d["totalStake"],
                    "averageOdd": d["averageOdd"],
                    "bestWinStreak": d.get("bestWinStreak"),
                }
                print(f"{d['profit']:+.4f}€")
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                print(f"KO ({e})")
                failed.append(f"{username}/{bm}")
            time.sleep(DELAY_SEC)

    if failed:
        print(f"\n⚠️  {len(failed)} échec(s) : {', '.join(failed)}")
        print("Relance le script pour retenter, ou continue avec les données partielles.")

    # Génération de data.py
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open("data.py", "w", encoding="utf-8") as f:
        f.write('"""\n')
        f.write(f"Données pré-calculées de la ligue MPP — généré le {generated_at}.\n")
        f.write("Ne pas éditer à la main : régénérer avec `python3 fetch_data.py`.\n")
        f.write('"""\n\n')
        f.write(f'GENERATED_AT = "{generated_at}"\n\n')
        f.write("LEAGUE_NAME = \"Coupe du Mao (à mao)\"\n\n")
        f.write("# (pseudo, prénom, rang MPP, points MPP)\n")
        f.write("LEAGUE = [\n")
        for u, fn, r, p in LEAGUE:
            f.write(f"    ({u!r}, {fn!r}, {r}, {p}),\n")
        f.write("]\n\n")
        f.write("# {bookmaker: {pseudo: {profit, roi, wins, bets, ...}}}\n")
        f.write("# Toutes les valeurs sont pour une mise de 1€ (linéaire, on multiplie à l'affichage).\n")
        f.write("DATA = ")
        # Pretty-print le dict Python
        f.write(_pretty_dict(data, indent=0))
        f.write("\n")

    print(f"\n✓ data.py écrit ({sum(len(v) for v in data.values())} entrées valides)")
    print(f"  Prochaine étape : commit data.py sur GitHub, l'app Streamlit va redéployer automatiquement.")


def _pretty_dict(d, indent=0):
    """Sérialise un dict Python de manière lisible."""
    if not isinstance(d, dict):
        return repr(d)
    pad = "    " * (indent + 1)
    close_pad = "    " * indent
    lines = ["{"]
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append(f"{pad}{k!r}: {_pretty_dict(v, indent+1)},")
        else:
            lines.append(f"{pad}{k!r}: {v!r},")
    lines.append(f"{close_pad}}}")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
