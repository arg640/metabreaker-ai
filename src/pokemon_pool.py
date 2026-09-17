# src/pokemon_pool.py
"""
Pool de Pokémon para el GA. Valida habilidades contra el pokedex de Showdown.
"""
import json
import re
from collections import Counter
from pathlib import Path


POOL_FILE = Path("data/processed/pool_data.json")
VALID_ABILITIES_FILE = Path("data/raw/valid_abilities.json")

POKEMON_EXCLUIDOS = {
    "Ditto",                  # Solo aprende Transform
    "Sinistcha-Masterpiece",  # Nombre >18 chars, Showdown lo rechaza
}


def _cargar_habilidades_validas() -> dict:
    if not VALID_ABILITIES_FILE.exists():
        print(f"⚠️  No existe {VALID_ABILITIES_FILE}. Corre primero:")
        print("    node scripts_fetch_abilities.js")
        return {}
    with open(VALID_ABILITIES_FILE, encoding="utf-8") as f:
        return json.load(f)


VALID_ABILITIES = _cargar_habilidades_validas()


def species_key(nombre: str) -> str:
    base = re.split(
        r"-(?:Mega|M|F|Hero|Midday|Midnight|Eternal|Hisui|Alola|Galar|Paldea|Dusk|Dawn|Busted|Blade|Crowned|Eternamax|Antique|Icy|Snow|Rainy|Sunny|River|Meadow|Polar|Tundra|Continental|Elegant|Garden|High|Plains|Modern|Monsoon|Ocean|Sandstorm|Savanna|Lemon|Mint|Ruby|Matcha|Salted|Caramel|Rainbow|Star)",
        nombre,
    )[0]
    return base.lower()


def _buscar_habilidades_validas(nombre: str) -> list | None:
    """Busca las habilidades válidas probando nombre exacto y variantes."""
    if nombre in VALID_ABILITIES:
        return VALID_ABILITIES[nombre]
    # Probar variantes comunes
    for variante in [nombre, nombre.capitalize(), nombre.lower()]:
        if variante in VALID_ABILITIES:
            return VALID_ABILITIES[variante]
    # Búsqueda case-insensitive
    nombre_lower = nombre.lower()
    for k, v in VALID_ABILITIES.items():
        if k.lower() == nombre_lower:
            return v
    # Búsqueda por species base (para formas como "Indeedee-F" -> "Indeedee")
    base = species_key(nombre)
    for k, v in VALID_ABILITIES.items():
        if species_key(k) == base:
            return v
    return None


def corregir_habilidad(p: dict) -> dict:
    """Si la habilidad no es válida para ese Pokémon, la reemplaza por una válida."""
    if not VALID_ABILITIES:
        return p

    nombre = p["pokemon"]
    ab_actual = p.get("ability") or ""

    if not ab_actual:
        return p

    validas = _buscar_habilidades_validas(nombre)
    if not validas:
        return p  # No sabemos qué habilidades tiene, dejamos como está

    if ab_actual in validas:
        return p  # Ya es válida

    # Corregir: usar la primera habilidad válida
    p = dict(p)
    p["ability"] = validas[0]
    return p


def limpiar_equipo(equipo: list[dict]) -> list[dict]:
    """Corrige habilidades, aplica Species Clause y Item Clause."""
    equipo_limpio = []
    especies_vistas = set()
    items_vistos = set()

    for p in equipo:
        if p["pokemon"] in POKEMON_EXCLUIDOS:
            continue

        p = corregir_habilidad(p)

        key = species_key(p["pokemon"])
        if key in especies_vistas:
            continue
        especies_vistas.add(key)

        item = p.get("item") or ""
        if item and item in items_vistos:
            p = dict(p)
            p["item"] = ""
        elif item:
            items_vistos.add(item)

        equipo_limpio.append(p)

    return equipo_limpio


def construir_pool() -> list[dict]:
    if not POOL_FILE.exists():
        raise FileNotFoundError(
            f"No existe {POOL_FILE}. Corre primero: python src/parse_api.py"
        )
    with open(POOL_FILE, encoding="utf-8") as f:
        pool = json.load(f)
    return [p for p in pool if p["pokemon"] not in POKEMON_EXCLUIDOS]


if __name__ == "__main__":
    pool = construir_pool()
    print(f"Pool total: {len(pool)} Pokémon")
    print(f"Habilidades válidas cargadas: {len(VALID_ABILITIES)} especies\n")

    keys = Counter(p["species_key"] for p in pool)
    duplicados = {k: v for k, v in keys.items() if v > 1}
    print(f"Species keys duplicados: {len(duplicados)}\n")

    print("Verificación de corrección de habilidades (primeros 20):")
    n_corregidas = 0
    for p in pool[:20]:
        original = p.get("ability") or "—"
        corregido = corregir_habilidad(p).get("ability") or "—"
        if original != corregido:
            print(f"  {p['pokemon']:<25} {original:<18} → {corregido}  ⚠️")
            n_corregidas += 1
        else:
            print(f"  {p['pokemon']:<25} {original:<18} (ok)")
    print(f"\nCorregidas en los primeros 20: {n_corregidas}")