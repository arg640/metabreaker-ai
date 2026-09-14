# src/parse_api.py
"""
Convierte el JSON crudo del API de Pikalytics en un pool limpio
con el mismo formato que el GA espera.

Filosofía: NO filtrar por uso. Solo descartar Pokémon con datos incompletos
(sin movimientos, habilidad, item o tipos). El GA se encarga de descartar
los malos por su fitness.

Salida: data/processed/pool_data.json
"""
import json
import re
from collections import Counter
from pathlib import Path


INPUT = Path("data/raw/pikalytics_api.json")
OUTPUT = Path("data/processed/pool_data.json")

# Solo requisitos mínimos de integridad
MIN_MOVES = 1              # Debe tener al menos 1 movimiento
MIN_ABILITIES = 1          # Debe tener al menos 1 habilidad
MIN_ITEMS = 1              # Debe tener al menos 1 item (algunos Pokémon no llevan)


def species_key(nombre: str) -> str:
    """Nombre base de la especie (sin sufijos de forma)."""
    base = re.split(
        r"-(?:Mega|M|F|Midday|Midnight|Eternal|Hisui|Alola|Galar|Paldea|Dusk|Dawn|Busted|Blade|Crowned|Eternamax)",
        nombre,
    )[0]
    return base.lower()


def parse_moves(moves_data: list[dict]) -> list[dict]:
    """Toma los 4 movimientos más usados."""
    if not moves_data:
        return []
    ordenados = sorted(moves_data, key=lambda m: float(m.get("percent", 0)), reverse=True)
    top4 = ordenados[:4]
    return [
        {"name": m["move"], "type": m.get("type", "normal").lower()}
        for m in top4
    ]


def parse_ability(abilities_data: list[dict]) -> str | None:
    if not abilities_data:
        return None
    ordenados = sorted(abilities_data, key=lambda a: float(a.get("percent", 0)), reverse=True)
    return ordenados[0]["ability"]


def parse_item(items_data: list[dict]) -> str | None:
    if not items_data:
        return None
    ordenados = sorted(items_data, key=lambda i: float(i.get("percent", 0)), reverse=True)
    return ordenados[0]["item"]


def parse_pokemon(entry: dict) -> tuple[dict | None, str]:
    """
    Convierte una entrada cruda en un dict del pool.
    Devuelve (parsed, motivo_descarte).
    """
    nombre = entry.get("name")
    if not nombre:
        return None, "sin_nombre"

    types = entry.get("types", [])
    if not types:
        return None, "sin_tipos"

    moves = parse_moves(entry.get("moves", []))
    if len(moves) < MIN_MOVES:
        return None, "sin_movimientos"

    abilities = entry.get("abilities", [])
    if len(abilities) < MIN_ABILITIES:
        return None, "sin_habilidad"

    items = entry.get("items", [])
    if len(items) < MIN_ITEMS:
        return None, "sin_item"

    ability = parse_ability(abilities)
    item = parse_item(items)

    return {
        "pokemon": nombre,
        "types": types,
        "ability": ability,
        "item": item,
        "moves": moves,
        "usage_pct": float(entry.get("percent", 0)),
        "species_key": species_key(nombre),
    }, "ok"


def main():
    if not INPUT.exists():
        print(f"❌ No existe {INPUT}. Corre primero src/scraper_api.py")
        return

    with open(INPUT, encoding="utf-8") as f:
        data = json.load(f)

    print(f"📥 Entradas en el JSON crudo: {len(data)}")
    print(f"🎯 Política: NO filtrar por uso, solo por datos incompletos\n")

    pool = []
    motivos = Counter()

    for entry in data:
        parsed, motivo = parse_pokemon(entry)
        if parsed is None:
            motivos[motivo] += 1
            continue
        pool.append(parsed)

    # Ordenar por uso descendente (solo para visualización)
    pool.sort(key=lambda p: p["usage_pct"], reverse=True)

    # Detectar species_key duplicados
    keys = Counter(p["species_key"] for p in pool)
    duplicados = {k: v for k, v in keys.items() if v > 1}

    # Guardar
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(pool, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Pool final: {len(pool)} Pokémon")
    print(f"\n📊 Descartados por datos incompletos:")
    for motivo, n in motivos.most_common():
        print(f"   {motivo}: {n}")

    print(f"\n📊 Species keys duplicados: {len(duplicados)}")
    for k, v in sorted(duplicados.items(), key=lambda x: -x[1])[:15]:
        formas = [p["pokemon"] for p in pool if p["species_key"] == k]
        print(f"   - {k}: {formas}")

    print(f"\n📊 Top 10 del pool (por uso):")
    for p in pool[:10]:
        tipos = "/".join(p["types"])
        print(f"   {p['pokemon']:<25} [{tipos:<20}] uso={p['usage_pct']:.2f}%")

    print(f"\n📊 Últimos 10 (los más raros que sobrevivieron):")
    for p in pool[-10:]:
        tipos = "/".join(p["types"])
        print(f"   {p['pokemon']:<25} [{tipos:<20}] uso={p['usage_pct']:.4f}%")

    print(f"\n✅ Guardado en: {OUTPUT}")


if __name__ == "__main__":
    main()