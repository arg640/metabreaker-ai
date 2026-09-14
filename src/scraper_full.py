# src/scraper_full.py
"""
Descarga los detalles de TODOS los Pokémon del meta actual desde Pikalytics.
- Primero obtiene la lista completa desde /api/l/...
- Luego hace una petición individual por cada Pokémon desde /api/p/.../{pokemon}
- Guarda todo en data/raw/pikalytics_full.json.
"""
import json
import time
from pathlib import Path

import requests

# Endpoints verificados
API_LIST = "https://www.pikalytics.com/api/l/2026-05/gen9championsvgc2026regmc-1760"
API_INDIVIDUAL = "https://www.pikalytics.com/api/p/2026-05/gen9championsvgc2026regmc-1760/{pokemon}"

# Delay entre requests (segundos) para no saturar el servidor
DELAY = 0.3

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_headers() -> dict:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.pikalytics.com/pokedex/gen9championsvgc2026regmc",
    }


def descargar_lista() -> list[dict]:
    print("⬇️  Descargando listado completo...")
    response = requests.get(API_LIST, headers=get_headers(), timeout=30)
    response.raise_for_status()
    data = response.json()
    print(f"✅ Lista descargada: {len(data)} Pokémon")
    return data


def descargar_pokemon(nombre: str) -> dict | None:
    """Descarga los detalles de un Pokémon individual."""
    nombre_url = (
        nombre.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace(".", "")
        .replace(":", "")
    )
    url = API_INDIVIDUAL.format(pokemon=nombre_url)

    try:
        response = requests.get(url, headers=get_headers(), timeout=15)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def main():
    # 1. Lista
    lista = descargar_lista()

    # 2. Detalles individuales
    print(f"\n⬇️  Descargando detalles de {len(lista)} Pokémon...")
    print(f"   Delay entre requests: {DELAY}s")
    print(f"   Tiempo estimado: {len(lista) * DELAY / 60:.1f} minutos\n")

    pokemon_completos = []
    fallos = []

    for i, entry in enumerate(lista, 1):
        nombre = entry.get("name", "")
        if not nombre:
            continue

        if i % 20 == 0 or i == len(lista):
            print(f"   [{i}/{len(lista)}] {nombre}...")

        detalle = descargar_pokemon(nombre)
        if detalle:
            pokemon_completos.append(detalle)
        else:
            fallos.append(nombre)

        time.sleep(DELAY)

    # 3. Guardar
    ruta = OUTPUT_DIR / "pikalytics_full.json"
    ruta.write_text(json.dumps(pokemon_completos, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n✅ Guardado: {ruta}")
    print(f"   Pokémon completos: {len(pokemon_completos)}")
    print(f"   Fallos: {len(fallos)}")
    if fallos:
        print(f"   Fallos (primeros 15): {fallos[:15]}")


if __name__ == "__main__":
    main()