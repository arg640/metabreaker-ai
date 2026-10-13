# src/pokemon_set.py
"""
Representa un PokemonSet con sistema de Stat Points de Champions.

Champions usa "Stat Points" (SP): 66 puntos totales, 32 máx por stat.
Es DIFERENTE a los EVs clásicos (510 total, 252 máx).

Reparto por arquetipo:
    fast_phys    -> 2 HP  / 32 Atk / 32 Spe     (Adamant / Jolly)
    fast_spec    -> 2 HP  / 32 SpA / 32 Spe     (Modest / Timid)
    bulky_phys   -> 32 HP / 32 Atk / 2 SpD      (Adamant)
    bulky_spec   -> 32 HP / 32 SpA / 2 SpD      (Modest)
    tr_phys      -> 32 HP / 32 Atk / 2 Def      (Brave)
    tr_spec      -> 32 HP / 32 SpA / 2 Def      (Quiet)
    support      -> 32 HP / 32 Def / 2 SpD (Bold)
                   32 HP / 2 Def / 32 SpD (Calm) según bulk
    wall_phys    -> 32 HP / 32 Def / 2 SpD      (Impish)
    wall_spec    -> 32 HP / 2 Def / 32 SpD      (Careful)
    mixed_fast   -> 2 HP  / 16 Atk / 16 SpA / 32 Spe (Naive)
    mixed_bulky  -> 32 HP / 16 Atk / 16 SpA / 2 SpD  (Naive)
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.config import BASE_STATS_FILE, PIKALYTICS_FULL


# ============================================================
# MAPEOS DE NOMBRES
# ============================================================
NOMBRES_CORTOS = {
    "Floette-Eternal-Mega": "Floette-Mega",
    "Floette-Eternal": "Floette-Mega",
}


# ============================================================
# STATS BASE
# ============================================================
def _cargar_stats_base() -> dict:
    if BASE_STATS_FILE.exists():
        with open(BASE_STATS_FILE, encoding="utf-8") as f:
            return json.load(f)

    if not PIKALYTICS_FULL.exists():
        print(f"[WARN]  No existe {BASE_STATS_FILE} ni {PIKALYTICS_FULL}")
        print(f"    Corre primero: node scripts_fetch_base_stats.js")
        return {}

    with open(PIKALYTICS_FULL, encoding="utf-8") as f:
        raw = json.load(f)

    stats_por_pokemon = {}
    for p in raw:
        nombre_raw = p.get("name", "")
        nombre_legible = p.get("name_trans") or p.get("display_name") or nombre_raw
        stats = p.get("stats", {})
        if stats and nombre_legible:
            stats_por_pokemon[nombre_legible] = stats
            if nombre_raw:
                stats_por_pokemon[nombre_raw.lower()] = stats
    return stats_por_pokemon


STATS_BASE = _cargar_stats_base()


def nombre_valido(nombre: str) -> str:
    if nombre in NOMBRES_CORTOS:
        return NOMBRES_CORTOS[nombre]
    if len(nombre) > 18:
        return nombre[:18]
    return nombre


def buscar_stats(nombre: str) -> dict:
    if nombre in STATS_BASE:
        return STATS_BASE[nombre]
    nombre_corto = nombre_valido(nombre)
    if nombre_corto in STATS_BASE:
        return STATS_BASE[nombre_corto]
    if nombre.lower() in STATS_BASE:
        return STATS_BASE[nombre.lower()]
    return {}


# ============================================================
# CATEGORÍA FÍSICO/ESPECIAL
# ============================================================
def detectar_categoria(nombre: str) -> str:
    """
    'fisico', 'especial' o 'mixto' según stats base.
    Regla: diferencia >15 puntos decide.
    """
    stats = buscar_stats(nombre)
    if not stats:
        return "mixto"

    atk = stats.get("atk", 0)
    spa = stats.get("spa", 0)

    if spa > atk + 15:
        return "especial"
    elif atk > spa + 15:
        return "fisico"
    return "mixto"


# ============================================================
# DETECCIÓN DE ARQUETIPO
# ============================================================
def _norm(name: str) -> str:
    return name.lower().replace(" ", "").replace("-", "").replace("'", "")


_MOVES_SOPORTE = {
    "fakeout", "followme", "ragepowder", "helpinghand", "partingshot",
    "willowisp", "encore", "taunt", "wideguard", "quickguard",
    "tailwind", "trickroom", "icywind", "snarl", "electroweb",
    "reflect", "lightscreen", "auroraveil", "safeguard", "coaching",
    "decorate", "lifedew", "skillswap", "topsyturvy", "spore",
    "sleeppowder", "quash", "afteryou", "allyswitch", "healpulse",
    "junglehealing", "chillyreception", "superfang",
}
_MOVES_TR = {"trickroom"}
_MOVES_TW = {"tailwind"}
_MOVES_SETUP = {
    "swordsdance", "nastyplot", "calmmind", "dragondance", "bulkup",
    "irondefense", "amnesia", "agility", "rockpolish", "shellsmash",
}
_MOVES_RECUPERACION = {
    "recover", "slackoff", "roost", "synthesis", "moonlight", "morningsun",
    "softboiled", "milkdrink", "shoreup", "strengthsap", "leechseed",
    "drainpunch", "gigadrain", "drainingkiss", "hornleech", "oblivionwing",
}


def _clasificar_arquetipo(pokemon_dict: dict) -> str:
    """Devuelve el nombre del arquetipo (clave de SPREADS)."""
    stats = buscar_stats(pokemon_dict.get("pokemon", ""))
    spe = stats.get("spe", 80)
    atk = stats.get("atk", 80)
    spa = stats.get("spa", 80)
    hp = stats.get("hp", 80)
    df = stats.get("def", 80)
    spd = stats.get("spd", 80)
    bulk = hp + df + spd

    moves = {
        _norm(m["name"])
        for m in pokemon_dict.get("moves", [])
        if m.get("name")
    }

    # 1) Trick Room user
    if moves & _MOVES_TR:
        return "tr_phys" if atk >= spa else "tr_spec"

    # 2) Soporte puro (movs de soporte sin setup y stats no ofensivos)
    tiene_soporte = bool(moves & _MOVES_SOPORTE)
    tiene_setup = bool(moves & _MOVES_SETUP)
    tiene_recup = bool(moves & _MOVES_RECUPERACION)

    if tiene_soporte and not tiene_setup and max(atk, spa) < 95:
        # Si tiene stats defensivos altos, es wall
        if tiene_recup and bulk > 250:
            return "wall_phys" if df >= spd else "wall_spec"
        return "support"

    # 3) Wall
    if tiene_recup and max(atk, spa) < 90 and bulk > 250:
        return "wall_phys" if df >= spd else "wall_spec"

    # 4) Diferenciar físico / especial / mixto
    diff = atk - spa
    if abs(diff) <= 15:
        return "mixed_fast" if spe >= 95 else "mixed_bulky"

    if diff > 0:  # físico
        if spe >= 95:
            return "fast_phys"
        return "bulky_phys" if bulk >= 260 else "fast_phys"

    # especial
    if spe >= 95:
        return "fast_spec"
    return "bulky_spec" if bulk >= 260 else "fast_spec"


# ============================================================
# SPREADS
# ============================================================
SPREADS: dict[str, tuple[dict[str, int], str]] = {
    "fast_phys":   ({"HP": 2,  "Atk": 32, "Spe": 32},              "Adamant"),
    "fast_spec":   ({"HP": 2,  "SpA": 32, "Spe": 32},              "Modest"),
    "bulky_phys":  ({"HP": 32, "Atk": 32, "SpD": 2},               "Adamant"),
    "bulky_spec":  ({"HP": 32, "SpA": 32, "SpD": 2},               "Modest"),
    "tr_phys":     ({"HP": 32, "Atk": 32, "Def": 2},               "Brave"),
    "tr_spec":     ({"HP": 32, "SpA": 32, "Def": 2},               "Quiet"),
    "wall_phys":   ({"HP": 32, "Def": 32, "SpD": 2},               "Impish"),
    "wall_spec":   ({"HP": 32, "Def": 2,  "SpD": 32},              "Careful"),
    "mixed_fast":  ({"HP": 2,  "Atk": 16, "SpA": 16, "Spe": 32},   "Naive"),
    "mixed_bulky": ({"HP": 32, "Atk": 16, "SpA": 16, "SpD": 2},    "Naive"),
}


def _spread_de(pokemon_dict: dict) -> tuple[dict[str, int], str]:
    """Devuelve (stat_points, nature) coherentes con el arquetipo."""
    arq = _clasificar_arquetipo(pokemon_dict)

    # Caso especial: support -> elige Bold o Calm según bulk
    if arq == "support":
        stats = buscar_stats(pokemon_dict.get("pokemon", ""))
        if stats.get("def", 80) >= stats.get("spd", 80):
            return {"HP": 32, "Def": 32, "SpD": 2}, "Bold"
        return {"HP": 32, "Def": 2, "SpD": 32}, "Calm"

    if arq in SPREADS:
        sp, nat = SPREADS[arq]
        return dict(sp), nat

    # Fallback razonable
    return {"HP": 2, "Atk": 32, "Spe": 32}, "Adamant"


# ============================================================
# DATA CLASS
# ============================================================
@dataclass
class PokemonSet:
    species: str
    moves: list[str]
    item: str = ""
    ability: str = ""
    level: int = 50
    nature: str = "Serious"
    stat_points: dict[str, int] = field(default_factory=dict)
    tera_type: Optional[str] = None

    def to_showdown(self) -> str:
        lineas = []
        species_corto = nombre_valido(self.species)
        nombre_item = species_corto
        if self.item:
            nombre_item += f" @ {self.item}"
        lineas.append(nombre_item)

        if self.ability:
            lineas.append(f"Ability: {self.ability}")

        lineas.append(f"Level: {self.level}")

        if self.tera_type:
            lineas.append(f"Tera Type: {self.tera_type}")

        if self.stat_points:
            ev_str = " / ".join(
                f"{v} {k}" for k, v in self.stat_points.items() if v > 0
            )
            if ev_str:
                lineas.append(f"EVs: {ev_str}")

        lineas.append(f"{self.nature} Nature")

        for move in self.moves:
            if move:
                lineas.append(f"- {move}")

        return "\n".join(lineas)

    @classmethod
    def from_dict(cls, data: dict) -> "PokemonSet":
        species = data["pokemon"]
        moves_data = data.get("moves", [])
        moves = [m["name"] for m in moves_data if m.get("name")]

        stat_points, nature = _spread_de(data)

        tera = data["types"][0].capitalize() if data.get("types") else None

        return cls(
            species=species,
            moves=moves,
            item=data.get("item") or "",
            ability=data.get("ability") or "",
            nature=nature,
            stat_points=stat_points,
            tera_type=tera,
        )


def equipo_a_showdown(equipo: list[dict]) -> str:
    sets = [PokemonSet.from_dict(p) for p in equipo]
    return "\n\n".join(s.to_showdown() for s in sets)


# ============================================================
# TEST RÁPIDO
# ============================================================
if __name__ == "__main__":
    print(f"Stats base cargados: {len(STATS_BASE)} Pokémon\n")

    ejemplos = [
        {"pokemon": "Rillaboom",
         "moves": [{"name": "Fake Out"}, {"name": "Grassy Glide"},
                   {"name": "Wood Hammer"}, {"name": "U-turn"}]},
        {"pokemon": "Flutter Mane",
         "moves": [{"name": "Moonblast"}, {"name": "Shadow Ball"},
                   {"name": "Icy Wind"}, {"name": "Protect"}]},
        {"pokemon": "Incineroar",
         "moves": [{"name": "Fake Out"}, {"name": "Flare Blitz"},
                   {"name": "Knock Off"}, {"name": "Parting Shot"}]},
        {"pokemon": "Amoonguss",
         "moves": [{"name": "Spore"}, {"name": "Rage Powder"},
                   {"name": "Pollen Puff"}, {"name": "Protect"}]},
        {"pokemon": "Iron Hands",
         "moves": [{"name": "Fake Out"}, {"name": "Drain Punch"},
                   {"name": "Wild Charge"}, {"name": "Detect"}]},
        {"pokemon": "Ursaluna-Bloodmoon",
         "moves": [{"name": "Blood Moon"}, {"name": "Earth Power"},
                   {"name": "Hyper Voice"}, {"name": "Protect"}]},
        {"pokemon": "Porygon2",
         "moves": [{"name": "Trick Room"}, {"name": "Ice Beam"},
                   {"name": "Recover"}, {"name": "Thunderbolt"}]},
    ]

    for p in ejemplos:
        arq = _clasificar_arquetipo(p)
        sp, nat = _spread_de(p)
        print(f"  {p['pokemon']:<22} -> {arq:<12} | {nat:<8} | {sp}")