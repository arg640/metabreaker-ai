# src/pokemon_pool.py
"""
Pool de Pokémon elegibles para el algoritmo genético.
También exporta `limpiar_equipo()`, que corrige habilidades inválidas
y aplica Species Clause / Item Clause a cualquier equipo (pool o rival).
"""
import json
import re
from collections import Counter


# Pokémon con datos irrecuperables en Pikalytics que rechazan equipos en Champions.
POKEMON_EXCLUIDOS = {
    "Lycanroc",
    "Lycanroc-Midday",
    "Lycanroc-Midnight",
    "Lycanroc-Dusk",
}


# Correcciones de habilidades inválidas en Pikalytics.
# (nombre_pokemon, habilidad_invalida) -> habilidad_valida en Champions.
HABILIDADES_CORREGIDAS = {
    ("Lycanroc", "Tough Claws"): "Sand Rush",
    ("Lycanroc-Midday", "Tough Claws"): "Sand Rush",
    ("Lycanroc-Midnight", "Tough Claws"): "No Guard",
    ("Lycanroc-Dusk", "Tough Claws"): "Tough Claws",
}


def species_key(nombre: str) -> str:
    """Nombre base de la especie (sin sufijos de forma) para Species Clause."""
    base = re.split(
        r"-(?:Mega|M|F|Midday|Midnight|Eternal|Hisui|Alola|Galar|Paldea|Dusk|Dawn|Busted|Blade|Crowned|Eternamax)",
        nombre,
    )[0]
    return base.lower()


def corregir_habilidad(p: dict) -> dict:
    """Devuelve una copia del Pokémon con la habilidad corregida si aplica."""
    key = (p["pokemon"], p.get("ability", ""))
    if key in HABILIDADES_CORREGIDAS:
        p = dict(p)
        p["ability"] = HABILIDADES_CORREGIDAS[key]
    return p


def limpiar_equipo(equipo: list[dict]) -> list[dict]:
    """
    Aplica todas las correcciones a un equipo antes de simular:
      1. Corrige habilidades inválidas.
      2. Aplica Species Clause (solo una forma por especie).
      3. Aplica Item Clause (solo un item por equipo).
    Devuelve un equipo nuevo (no modifica el original).
    """
    # Paso 1: corregir habilidades y descartar Pokémon problemáticos
    equipo_limpio = []
    especies_vistas = set()
    items_vistos = set()

    for p in equipo:
        # Descartar Pokémon excluidos
        if p["pokemon"] in POKEMON_EXCLUIDOS:
            continue

        # Corregir habilidad
        p = corregir_habilidad(p)

        # Species Clause: solo una forma por especie
        key = species_key(p["pokemon"])
        if key in especies_vistas:
            continue
        especies_vistas.add(key)

        # Item Clause: solo un item por equipo
        item = p.get("item") or ""
        if item and item in items_vistos:
            p = dict(p)
            p["item"] = ""
        elif item:
            items_vistos.add(item)

        equipo_limpio.append(p)

    return equipo_limpio


def construir_pool(min_apariciones: int = 1) -> list[dict]:
    """Construye el pool de Pokémon candidatos a partir del sample_teams.json."""
    with open("data/processed/sample_teams.json", encoding="utf-8") as f:
        equipos = json.load(f)

    apariciones = Counter()
    datos_por_pokemon = {}

    for equipo in equipos:
        for p in equipo:
            nombre = p["pokemon"]
            if nombre in POKEMON_EXCLUIDOS:
                continue
            apariciones[nombre] += 1
            if nombre not in datos_por_pokemon:
                datos_por_pokemon[nombre] = p

    pool = []
    for nombre, count in apariciones.most_common():
        if count >= min_apariciones:
            entry = dict(datos_por_pokemon[nombre])
            entry["apariciones"] = count
            entry["species_key"] = species_key(nombre)
            entry = corregir_habilidad(entry)
            pool.append(entry)

    return pool


if __name__ == "__main__":
    pool = construir_pool()
    print(f"Pool total: {len(pool)} Pokémon únicos\n")

    keys = Counter(p["species_key"] for p in pool)
    duplicados = {k: v for k, v in keys.items() if v > 1}
    if duplicados:
        print(f"⚠️ Species keys duplicados (el GA solo elegirá uno):")
        for k, v in duplicados.items():
            print(f"   - {k}: {v} formas")
        print()

    for i, p in enumerate(pool):
        tipos = "/".join(p["types"])
        print(f"  [{i:>2}] {p['pokemon']:<25} [{tipos:<22}] key={p['species_key']}")