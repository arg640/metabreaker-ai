# src/parse_api.py
"""
Convierte data/raw/pikalytics_full.json en pool_data.json.

Filosofía:
- NO filtrar por uso. Solo descartar Pokémon con datos insuficientes
  (< MIN_GAMES partidas) o datos críticos incompletos (types, moves).
- Usar name_trans para el nombre correctamente formateado.
- Si falta habilidad o item, dejar en blanco.
"""
import json
import re
from collections import Counter
from pathlib import Path


INPUT = Path("data/raw/pikalytics_full.json")
OUTPUT = Path("data/processed/pool_data.json")

# Requisitos mínimos
MIN_MOVES = 1
MIN_TYPES = 1
MIN_GAMES = 50   # Filtro de calidad de datos, no de popularidad


def species_key(nombre: str) -> str:
    """Nombre base de la especie (sin sufijos de forma)."""
    base = re.split(
        r"-(?:Mega|M|F|Midday|Midnight|Eternal|Hisui|Alola|Galar|Paldea|Dusk|Dawn|Busted|Blade|Crowned|Eternamax|Antique|Icy|Snow|Rainy|Sunny|River|Meadow|Polar|Tundra|Continental|Elegant|Garden|High|Plains|Modern|Monsoon|Ocean|Sandstorm|Savanna|Lemon|Mint|Ruby|Matcha|Salted|Caramel|Rainbow|Star)",
        nombre,
    )[0]
    return base.lower()


def nombre_legible(entry: dict) -> str | None:
    """Devuelve el nombre correctamente formateado."""
    return entry.get("name_trans") or entry.get("display_name") or entry.get("name")


def parse_moves(moves_data: list) -> list:
    if not moves_data:
        return []
    ordenados = sorted(
        moves_data,
        key=lambda m: float(m.get("percent", 0) or 0),
        reverse=True,
    )
    return [
        {"name": m["move"], "type": (m.get("type") or "normal").lower()}
        for m in ordenados[:4]
        if m.get("move")
    ]


def parse_ability(abilities_data: list) -> str | None:
    if not abilities_data:
        return None
    ordenados = sorted(
        abilities_data,
        key=lambda a: float(a.get("percent", 0) or 0),
        reverse=True,
    )
    return ordenados[0].get("ability") if ordenados else None


def parse_item(items_data: list) -> str | None:
    if not items_data:
        return None
    ordenados = sorted(
        items_data,
        key=lambda i: float(i.get("percent", 0) or 0),
        reverse=True,
    )
    return ordenados[0].get("item") if ordenados else None


def parse_pokemon(entry: dict) -> tuple[dict | None, str]:
    nombre_raw = entry.get("name")
    if not nombre_raw:
        return None, "sin_nombre"

    nombre = nombre_legible(entry)
    if not nombre:
        return None, "sin_nombre_legible"

    # Filtro por partidas mínimas
    try:
        games = int(entry.get("games", 0) or 0)
    except (ValueError, TypeError):
        games = 0
    if games < MIN_GAMES:
        return None, "pocas_partidas"

    types = entry.get("types") or []
    if len(types) < MIN_TYPES:
        return None, "sin_tipos"

    moves = parse_moves(entry.get("moves") or [])
    if len(moves) < MIN_MOVES:
        return None, "sin_movimientos"

    ability = parse_ability(entry.get("abilities") or [])
    item = parse_item(entry.get("items") or [])

    usage = float(entry.get("percent", 0) or 0)

    return {
        "pokemon": nombre,
        "types": types,
        "ability": ability,
        "item": item,
        "moves": moves,
        "usage_pct": usage,
        "games": games,
        "species_key": species_key(nombre_raw),
    }, "ok"


def main():
    if not INPUT.exists():
        print(f"❌ No existe {INPUT}. Corre primero src/scraper_full.py")
        return

    with open(INPUT, encoding="utf-8") as f:
        data = json.load(f)

    print(f"📥 Entradas en el JSON crudo: {len(data)}\n")

    pool = []
    motivos = Counter()

    for entry in data:
        parsed, motivo = parse_pokemon(entry)
        if parsed is None:
            motivos[motivo] += 1
            continue
        pool.append(parsed)

    pool.sort(key=lambda p: p["usage_pct"], reverse=True)

    keys = Counter(p["species_key"] for p in pool)
    duplicados = {k: v for k, v in keys.items() if v > 1}

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(pool, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Pool final: {len(pool)} Pokémon")
    print(f"\n📊 Descartados:")
    for motivo, n in motivos.most_common():
        print(f"   {motivo}: {n}")

    print(f"\n📊 Species keys duplicados: {len(duplicados)}")
    for k, v in sorted(duplicados.items(), key=lambda x: -x[1])[:10]:
        formas = [p["pokemon"] for p in pool if p["species_key"] == k]
        print(f"   - {k}: {formas}")

    print(f"\n📊 Top 10 del pool:")
    for p in pool[:10]:
        tipos = "/".join(p["types"])
        ab = p["ability"] or "—"
        it = p["item"] or "—"
        print(f"   {p['pokemon']:<25} [{tipos:<20}] uso={p['usage_pct']:.2f}%  ab={ab:<15} item={it}")

    print(f"\n📊 Últimos 5 (los más raros que pasaron el filtro):")
    for p in pool[-5:]:
        tipos = "/".join(p["types"])
        print(f"   {p['pokemon']:<25} [{tipos:<20}] uso={p['usage_pct']:.4f}%  games={p['games']}")

    print(f"\n✅ Guardado en: {OUTPUT}")


if __name__ == "__main__":
    main()