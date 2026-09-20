# src/pokemon_pool.py
"""
Pool de Pokémon para el GA.
- Valida habilidades contra el pokedex de Showdown.
- Filtra formas duplicadas (se queda con la más usada del meta).
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
    """Nombre base de la especie (sin sufijos de forma) para Species Clause."""
    base = re.split(
        r"-(?:Mega|M|F|Hero|Midday|Midnight|Eternal|Hisui|Alola|Galar|Paldea|Dusk|Dawn|Busted|Blade|Crowned|Eternamax|Antique|Icy|Snow|Rainy|Sunny|River|Meadow|Polar|Tundra|Continental|Elegant|Garden|High|Plains|Modern|Monsoon|Ocean|Sandstorm|Savanna|Lemon|Mint|Ruby|Matcha|Salted|Caramel|Rainbow|Star)",
        nombre,
    )[0]
    return base.lower()


def _buscar_habilidades_validas(nombre: str) -> list | None:
    """Busca las habilidades válidas probando nombre exacto y variantes."""
    if nombre in VALID_ABILITIES:
        return VALID_ABILITIES[nombre]
    for variante in [nombre, nombre.capitalize(), nombre.lower()]:
        if variante in VALID_ABILITIES:
            return VALID_ABILITIES[variante]
    nombre_lower = nombre.lower()
    for k, v in VALID_ABILITIES.items():
        if k.lower() == nombre_lower:
            return v
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
        return p

    if ab_actual in validas:
        return p

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
    """
    Carga el pool desde el JSON generado por parse_api.py.
    Filtra formas duplicadas: cuando dos Pokémon comparten species_key,
    se queda con el de MAYOR usage.
    """
    if not POOL_FILE.exists():
        raise FileNotFoundError(
            f"No existe {POOL_FILE}. Corre primero: python src/parse_api.py"
        )
    with open(POOL_FILE, encoding="utf-8") as f:
        pool = json.load(f)

    # Filtrar excluidos
    pool = [p for p in pool if p["pokemon"] not in POKEMON_EXCLUIDOS]

    # Agrupar por species_key y quedarse con la forma más usada
    por_key: dict[str, dict] = {}
    for p in pool:
        key = species_key(p["pokemon"])
        if key not in por_key:
            por_key[key] = p
        else:
            if p.get("usage_pct", 0) > por_key[key].get("usage_pct", 0):
                por_key[key] = p

    return list(por_key.values())


if __name__ == "__main__":
    pool = construir_pool()
    print(f"Pool total: {len(pool)} Pokémon (filtrado por forma más usada)")
    print(f"Habilidades válidas cargadas: {len(VALID_ABILITIES)} especies\n")

    # Verificar formas colapsadas
    print("Verificación de formas colapsadas:")
    for p in pool:
        nombre_lower = p["pokemon"].lower()
        if "indeedee" in nombre_lower:
            print(f"  Indeedee seleccionada: {p['pokemon']} (usage={p['usage_pct']:.2f}%)")
        if "sinistcha" in nombre_lower:
            print(f"  Sinistcha seleccionada: {p['pokemon']} (usage={p['usage_pct']:.2f}%)")
        if "palafin" in nombre_lower:
            print(f"  Palafin seleccionada: {p['pokemon']} (usage={p['usage_pct']:.2f}%)")

    keys = Counter(species_key(p["pokemon"]) for p in pool)
    duplicados = {k: v for k, v in keys.items() if v > 1}
    if duplicados:
        print(f"\n⚠️  Aún hay duplicados: {duplicados}")
    else:
        print(f"\n✅ Sin duplicados de species_key")

    print(f"\nPrimeros 15:")
    for i, p in enumerate(pool[:15]):
        tipos = "/".join(p["types"])
        ab = p["ability"] or "—"
        print(f"  [{i:>3}] {p['pokemon']:<25} [{tipos:<20}] usage={p['usage_pct']:.2f}%  ab={ab}")