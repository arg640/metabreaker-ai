# src/pokemon_pool.py
"""
Pool de Pokémon para el GA.

- Habilidades, ítems requeridos y LEARNSETS validados contra el Dex de
  Showdown (mod "champions").
- Formas duplicadas colapsadas (se queda con la más usada) EXCEPTO megas,
  que son opciones independientes del pool.
- limpiar_equipo() aplica:
    * Resolución de species (Indeedee → Indeedee-F/M según moves)
    * Filtrado de moves inválidos contra el learnset oficial
    * Species Clause
    * Item Clause con fallbacks inteligentes
    * Mega Clause: máximo 2 megas con piedra por equipo
    * Item requerido forzado para megas y formas
    * Corrección de habilidades contra species_full.json
"""
import json
import re

from src.config import POOL_FILE, RAW_DIR, VALID_ABILITIES_FILE
from src.pokemon_set import _clasificar_arquetipo


POKEMON_EXCLUIDOS = {
    "Ditto",                  # Solo aprende Transform
    "Sinistcha-Masterpiece",  # Nombre >18 chars, Showdown lo rechaza
}

VALID_ITEMS_FILE = RAW_DIR / "valid_items.json"
SPECIES_FULL_FILE = RAW_DIR / "species_full.json"
LEARNSETS_FILE = RAW_DIR / "learnsets.json"

# Límite de megas con piedra por equipo (Champions permite hasta 2)
MAX_MEGAS_POR_EQUIPO = 2


# ============================================================
# CARGA DE DATOS DEL DEX
# ============================================================
def _cargar_habilidades_validas() -> dict:
    if not VALID_ABILITIES_FILE.exists():
        print(f"[WARN] No existe {VALID_ABILITIES_FILE}. Corre primero:")
        print("    node scripts_fetch_abilities.js")
        return {}
    with open(VALID_ABILITIES_FILE, encoding="utf-8") as f:
        return json.load(f)


def _cargar_species_full() -> dict:
    if not SPECIES_FULL_FILE.exists():
        print(f"[WARN] No existe {SPECIES_FULL_FILE}. Corre primero:")
        print("    node scripts_fetch_species_full.js")
        return {}
    with open(SPECIES_FULL_FILE, encoding="utf-8") as f:
        return json.load(f)


def _cargar_items_validos() -> set:
    if not VALID_ITEMS_FILE.exists():
        print(f"[WARN] No existe {VALID_ITEMS_FILE}. Corre primero:")
        print("    node scripts_fetch_valid_items.js")
        return set()
    with open(VALID_ITEMS_FILE, encoding="utf-8") as f:
        return set(json.load(f))


def _cargar_learnsets() -> dict:
    if not LEARNSETS_FILE.exists():
        print(f"[WARN] No existe {LEARNSETS_FILE}. Corre primero:")
        print("    node scripts_fetch_learnsets.js")
        print("    (Sin esta lista, no se filtrarán moves inválidos.)")
        return {}
    with open(LEARNSETS_FILE, encoding="utf-8") as f:
        return json.load(f)


VALID_ABILITIES = _cargar_habilidades_validas()
SPECIES_FULL = _cargar_species_full()
VALID_ITEMS = _cargar_items_validos()
LEARNSETS = _cargar_learnsets()


def _es_item_valido(item: str) -> bool:
    if not item:
        return False
    if not VALID_ITEMS:
        return True
    return item in VALID_ITEMS


def _species_data(nombre: str) -> dict:
    """Devuelve la info del Dex para un nombre. {} si no existe."""
    if nombre in SPECIES_FULL:
        return SPECIES_FULL[nombre]
    for variante in [nombre.capitalize(), nombre.lower()]:
        if variante in SPECIES_FULL:
            return SPECIES_FULL[variante]
    return {}


# ============================================================
# SPECIES KEY
# ============================================================
def species_key(nombre: str) -> str:
    base = re.split(
        r"-(?:Mega|M|F|Hero|Midday|Midnight|Eternal|Hisui|Alola|Galar|Paldea|"
        r"Dusk|Dawn|Busted|Blade|Crowned|Eternamax|Antique|Icy|Snow|Rainy|"
        r"Sunny|River|Meadow|Polar|Tundra|Continental|Elegant|Garden|High|"
        r"Plains|Modern|Monsoon|Ocean|Sandstorm|Savanna|Lemon|Mint|Ruby|"
        r"Matcha|Salted|Caramel|Rainbow|Star|Wash|Heat|Mow|Frost|Fan)",
        nombre,
    )[0]
    return base.lower()


# ============================================================
# DETECCIÓN DE MEGA CON PIEDRA
# ============================================================
def _es_mega_stone(item: str) -> bool:
    if not item:
        return False
    low = item.strip()
    if low.endswith("ite") or low.endswith("ite X") or low.endswith("ite Y"):
        return True
    return False


def _es_mega_con_piedra(nombre: str, required_item: str | None) -> bool:
    if not required_item:
        return False
    if "Mega" in nombre:
        return True
    return _es_mega_stone(required_item)


# ============================================================
# LEARNSETS — utilidades
# ============================================================
def _norm_move(name: str) -> str:
    """'Follow Me' -> 'followme'; 'U-turn' -> 'uturn'."""
    return name.lower().replace(" ", "").replace("-", "").replace("'", "")


def _moves_legales(species: str) -> set | None:
    """Set normalizado de moves legales. None si no tenemos info."""
    raw = LEARNSETS.get(species)
    if raw is None:
        return None
    return {_norm_move(m) for m in raw}


def _resolver_species(nombre: str, moves: list[dict]) -> str | None:
    """
    Devuelve el nombre de species del Dex que mejor matchea con los moves
    dados. Útil para casos como Indeedee (Pikalytics mezcla M y F):
    - Si 'Indeedee' existe en el Dex, devolverlo.
    - Si no, probar 'Indeedee-F' e 'Indeedee-M' y elegir el que más moves
      comparta con el learnset oficial.
    - Devolver None si nada matchea.
    """
    # Caso 1: nombre exacto existe en el Dex
    if _species_data(nombre):
        return nombre

    # Caso 2: probar variantes
    nombre_norm = _norm_move(nombre)
    candidatos = [
        f"{nombre}-F", f"{nombre}-M",
        f"{nombre}-Female", f"{nombre}-Male",
        nombre_norm.capitalize(),
    ]
    moves_norm = {_norm_move(m["name"]) for m in moves if m.get("name")}

    mejor = None
    mejor_score = -1
    for cand in candidatos:
        if not _species_data(cand):
            continue
        legales = _moves_legales(cand)
        if not legales:
            continue
        matches = len(moves_norm & legales)
        if matches > mejor_score:
            mejor_score = matches
            mejor = cand

    return mejor  # puede ser None


def limpiar_moves(pokemon_dict: dict) -> dict | None:
    """
    Filtra los moves que la species no puede aprender.
    Devuelve None si quedaron 0 moves válidos.
    """
    nombre = pokemon_dict["pokemon"]
    legales = _moves_legales(nombre)
    if legales is None:
        return pokemon_dict  # sin info, dejamos pasar

    moves_ok = [
        m for m in pokemon_dict.get("moves", [])
        if _norm_move(m.get("name", "")) in legales
    ]
    if not moves_ok:
        return None

    if len(moves_ok) == len(pokemon_dict.get("moves", [])):
        return pokemon_dict

    p = dict(pokemon_dict)
    p["moves"] = moves_ok
    return p


# ============================================================
# HABILIDADES
# ============================================================
def _buscar_habilidades_validas(nombre: str) -> list | None:
    datos = _species_data(nombre)
    if datos.get("abilities"):
        return datos["abilities"]
    if nombre in VALID_ABILITIES:
        return VALID_ABILITIES[nombre]
    base = species_key(nombre)
    for k, v in VALID_ABILITIES.items():
        if species_key(k) == base:
            return v
    return None


def corregir_habilidad(p: dict) -> dict:
    nombre = p["pokemon"]
    ab_actual = p.get("ability") or ""
    validas = _buscar_habilidades_validas(nombre)
    if not validas:
        return p
    if ab_actual in validas:
        return p
    p = dict(p)
    p["ability"] = validas[0]
    return p


# ============================================================
# ÍTEMS
# ============================================================
FALLBACK_ITEMS: dict[str, list[str]] = {
    "fast_phys":   ["Focus Sash", "Life Orb", "Sitrus Berry", "Clear Amulet"],
    "fast_spec":   ["Focus Sash", "Life Orb", "Sitrus Berry", "Choice Specs"],
    "bulky_phys":  ["Sitrus Berry", "Rocky Helmet", "Covert Cloak", "Leftovers"],
    "bulky_spec":  ["Sitrus Berry", "Leftovers", "Covert Cloak", "Safety Goggles"],
    "tr_phys":     ["Sitrus Berry", "Mental Herb", "Clear Amulet", "Life Orb"],
    "tr_spec":     ["Sitrus Berry", "Mental Herb", "Life Orb", "Throat Spray"],
    "support":     ["Sitrus Berry", "Focus Sash", "Mental Herb", "Covert Cloak",
                    "Safety Goggles"],
    "wall_phys":   ["Leftovers", "Rocky Helmet", "Sitrus Berry", "Covert Cloak"],
    "wall_spec":   ["Leftovers", "Sitrus Berry", "Covert Cloak", "Safety Goggles"],
    "mixed_fast":  ["Life Orb", "Sitrus Berry", "Focus Sash"],
    "mixed_bulky": ["Life Orb", "Sitrus Berry"],
}


def _fallback_item(pokemon_dict: dict, usados: set) -> str:
    try:
        arq = _clasificar_arquetipo(pokemon_dict)
    except Exception:
        arq = "support"
    pool = FALLBACK_ITEMS.get(arq, FALLBACK_ITEMS["support"])
    for item in pool:
        if item in usados:
            continue
        if not _es_item_valido(item):
            continue
        return item
    for item in ["Sitrus Berry", "Focus Sash", "Leftovers", "Life Orb"]:
        if item not in usados and _es_item_valido(item):
            return item
    return ""


# ============================================================
# LIMPIEZA DE EQUIPO
# ============================================================
def limpiar_equipo(equipo: list[dict]) -> list[dict]:
    """
    Reglas (en orden):
    1. Excluir Pokémon prohibidos o species inexistentes.
    2. Especies con requiredItem (megas, formas): forzar ese item.
       Mega Clause: máximo MAX_MEGAS_POR_EQUIPO megas con piedra.
    3. Filtrar moves inválidos contra el learnset oficial.
    4. Species Clause.
    5. Corregir habilidad contra species_full.json.
    6. Item Clause + fallbacks para el resto.
    """
    equipo_limpio: list[dict] = []
    especies_vistas: set[str] = set()
    items_usados: set[str] = set()
    megas_con_piedra = 0

    for p in equipo:
        if p["pokemon"] in POKEMON_EXCLUIDOS:
            continue

        # --- Resolver species (Indeedee -> Indeedee-F/M según moves) ---
        movs = p.get("moves", [])
        nombre_resuelto = _resolver_species(p["pokemon"], movs)
        if not nombre_resuelto:
            continue  # species inexistente en el Dex

        p = dict(p)
        if nombre_resuelto != p["pokemon"]:
            p["pokemon"] = nombre_resuelto
            p["species_key"] = species_key(nombre_resuelto)

        # --- Filtrar moves inválidos ---
        p = limpiar_moves(p)
        if p is None:
            continue  # quedó sin moves válidos

        datos = _species_data(p["pokemon"])
        required_item = datos.get("requiredItem")
        es_mega = _es_mega_con_piedra(p["pokemon"], required_item)

        # --- Mega Clause ---
        if es_mega and megas_con_piedra >= MAX_MEGAS_POR_EQUIPO:
            continue

        # --- Species Clause ---
        key = species_key(p["pokemon"])
        if key in especies_vistas:
            continue
        especies_vistas.add(key)

        # --- Habilidad ---
        p = corregir_habilidad(p)
        p = dict(p)

        # --- Item requerido (megas, formas) ---
        if required_item:
            p["item"] = required_item
            items_usados.add(required_item)
            if es_mega:
                megas_con_piedra += 1
        else:
            item = (p.get("item") or "").strip()
            if item and not _es_item_valido(item):
                item = ""
            if item and item in items_usados:
                nuevo = _fallback_item(p, items_usados)
                p["item"] = nuevo
                if nuevo:
                    items_usados.add(nuevo)
            elif item:
                p["item"] = item
                items_usados.add(item)
            else:
                nuevo = _fallback_item(p, items_usados)
                p["item"] = nuevo
                if nuevo:
                    items_usados.add(nuevo)

        equipo_limpio.append(p)

    return equipo_limpio


# ============================================================
# CONSTRUCCIÓN DEL POOL
# ============================================================
def _inyectar_megas(pool: list[dict]) -> list[dict]:
    """
    Agrega al pool las formas Mega que existan en el Dex y cuyo baseSpecies
    ya esté en el pool. Usa moves/types del base pero fuerza la habilidad
    y el item requerido de la mega.
    """
    por_nombre = {p["pokemon"]: p for p in pool}
    extras: list[dict] = []

    for nombre, datos in SPECIES_FULL.items():
        if "Mega" not in nombre:
            continue
        if nombre in por_nombre:
            continue
        base = datos.get("baseSpecies")
        if not base or base not in por_nombre:
            continue

        base_p = por_nombre[base]
        nuevo = dict(base_p)
        nuevo["pokemon"] = nombre
        nuevo["item"] = datos.get("requiredItem") or ""
        nuevo["species_key"] = nombre.lower()
        nuevo["usage_pct"] = base_p.get("usage_pct", 0) * 0.5

        ab_mega = datos.get("abilities") or []
        if ab_mega:
            nuevo["ability"] = ab_mega[0]

        extras.append(nuevo)

    return pool + extras


def _resolver_nombre_en_pool(p: dict) -> dict | None:
    """
    Resuelve el nombre de un Pokémon del pool crudo (data/processed/pool_data.json)
    al nombre oficial del Dex. Devuelve el dict modificado o None si no se pudo.
    """
    nombre = p["pokemon"]
    if _species_data(nombre):
        return p  # ya está bien

    # Probar variantes (Indeedee -> Indeedee-F/M)
    resuelto = _resolver_species(nombre, p.get("moves", []))
    if not resuelto:
        return None

    p = dict(p)
    p["pokemon"] = resuelto
    p["species_key"] = species_key(resuelto)

    # Filtrar moves inválidos
    p = limpiar_moves(p)
    return p  # puede ser None si quedó sin moves


def construir_pool() -> list[dict]:
    if not POOL_FILE.exists():
        raise FileNotFoundError(
            f"No existe {POOL_FILE}. Corre primero: python src/parse_api.py"
        )
    with open(POOL_FILE, encoding="utf-8") as f:
        pool = json.load(f)

    pool = [p for p in pool if p["pokemon"] not in POKEMON_EXCLUIDOS]

    # Resolver nombres + limpiar moves
    pool_resuelto: list[dict] = []
    for p in pool:
        r = _resolver_nombre_en_pool(p)
        if r is not None:
            pool_resuelto.append(r)
    pool = pool_resuelto

    # Inyectar megas legales
    pool = _inyectar_megas(pool)

    # Colapsar duplicados (uno por species_key, salvo megas)
    por_key: dict[str, dict] = {}
    for p in pool:
        nombre = p["pokemon"]
        if "Mega" in nombre:
            key = nombre.lower()
        else:
            key = species_key(nombre)

        if key not in por_key:
            por_key[key] = p
        elif p.get("usage_pct", 0) > por_key[key].get("usage_pct", 0):
            por_key[key] = p

    return list(por_key.values())


if __name__ == "__main__":
    pool = construir_pool()
    n_megas = sum(
        1 for p in pool
        if _es_mega_con_piedra(p["pokemon"], _species_data(p["pokemon"]).get("requiredItem"))
    )
    print(f"Pool total: {len(pool)} Pokemon")
    print(f"  Megas con piedra en el pool: {n_megas}")
    print(f"  Limite por equipo:           {MAX_MEGAS_POR_EQUIPO}")
    print(f"Habilidades validas:           {len(VALID_ABILITIES)} especies")
    print(f"Items validos:                 {len(VALID_ITEMS)}")
    print(f"Species en el Dex:             {len(SPECIES_FULL)}")
    print(f"Learnsets cargados:            {len(LEARNSETS)} species\n")

    # Test Mega Clause
    print("Test Mega Clause (3 megas -> debe quedar 2):")
    equipo_test = [
        {"pokemon": "Charizard-Mega-Y", "types": ["fire", "flying"],
         "item": "Charizardite Y", "moves": [{"name": "Heat Wave"}], "ability": "Drought"},
        {"pokemon": "Gengar-Mega", "types": ["ghost", "poison"],
         "item": "Gengarite", "moves": [{"name": "Shadow Ball"}], "ability": "Shadow Tag"},
        {"pokemon": "Raichu-Mega-Y", "types": ["electric"],
         "item": "Raichunite Y", "moves": [{"name": "Thunderbolt"}], "ability": "No Guard"},
        {"pokemon": "Rillaboom", "types": ["grass"],
         "item": "Assault Vest", "moves": [{"name": "Grassy Glide"}], "ability": "Grassy Surge"},
    ]
    resultado = limpiar_equipo(equipo_test)
    for p in resultado:
        mega_tag = "[MEGA]" if _es_mega_con_piedra(
            p["pokemon"], _species_data(p["pokemon"]).get("requiredItem")
        ) else "      "
        print(f"  {mega_tag} {p['pokemon']:<25} @ {p.get('item') or '(sin item)'}")
    print()

    # Test Indeedee (el caso problemático)
    print("Test Indeedee (macho/hembra por moves):")
    eq_indeedee = [
        {"pokemon": "Indeedee", "types": ["psychic", "normal"],
         "item": "", "moves": [
             {"name": "Follow Me", "type": "normal"},
             {"name": "Psychic", "type": "psychic"},
             {"name": "Helping Hand", "type": "normal"},
             {"name": "Trick Room", "type": "psychic"},
         ], "ability": "Psychic Surge"},
    ]
    resultado = limpiar_equipo(eq_indeedee)
    for p in resultado:
        moves_txt = ", ".join(m["name"] for m in p.get("moves", []))
        print(f"  {p['pokemon']:<20} | moves: {moves_txt}")
        print(f"  ability: {p.get('ability')} | item: {p.get('item') or '(sin item)'}")
    print()

    # Test limpiar equipo de muestra
    from src.config import SAMPLE_TEAMS_FILE
    if SAMPLE_TEAMS_FILE.exists():
        with open(SAMPLE_TEAMS_FILE, encoding="utf-8") as f:
            equipos = json.load(f)
        test = limpiar_equipo(equipos[0])
        print("Test limpiar_equipo (equipo 0):")
        for p in test:
            arq = _clasificar_arquetipo(p)
            item = p.get("item") or "(sin item)"
            valido = "OK" if _es_item_valido(item) else "INVALIDO"
            n_moves = len(p.get("moves", []))
            print(f"  {p['pokemon']:<25} [{arq:<12}] @ {item:<22} [{valido}] ({n_moves} moves)")