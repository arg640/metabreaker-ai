# src/scraper_api.py
"""
Descarga el JSON completo del meta actual desde el endpoint interno de Pikalytics.
Una sola petición HTTP devuelve TODOS los Pokémon con sus stats, items, moves, etc.
"""
import json
from pathlib import Path

import requests


# Endpoint descubierto en DevTools (Network > Fetch/XHR).
# El sufijo 1760 indica Elo 1760+ (top ladder).
API_URL = "https://www.pikalytics.com/api/l/2026-05/gen9championsvgc2026regmc-1760"

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def descargar_json(url: str, nombre_archivo: str) -> None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.pikalytics.com/pokedex/gen9championsvgc2026regmc",
    }

    print(f"⬇️  Descargando {url}...")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()

    ruta = OUTPUT_DIR / nombre_archivo
    ruta.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Guardado: {ruta}")
    print(f"📊 Tipo de dato: {type(data).__name__}")
    if isinstance(data, list):
        print(f"📊 Total de Pokémon: {len(data)}")
        if data:
            print(f"📊 Top 5: {[p.get('name') for p in data[:5]]}")
            print(f"📊 Último: {data[-1].get('name')}")


if __name__ == "__main__":
    descargar_json(API_URL, "pikalytics_api.json")