# src/pokemon_set.py
"""
Representa un PokemonSet con sistema de Stat Points de Champions.
Detecta automáticamente si un Pokémon es físico o especial usando sus STATS BASE.
Fuente de stats: base_stats.json (descargado de Showdown con scripts_fetch_base_stats.js).
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Nombres de especies que necesitan mapeo especial
NOMBRES_CORTOS = {
    "Floette-Eternal-Mega": "Floette-Mega",
    "Floette-Eternal": "Floette-Mega",
}


def _cargar_stats_base() -> dict:
    """
    Carga stats base desde Showdown (data/raw/base_stats.json) si existe.
    Fallback: pikalytics_full.json.
    """
    showdown_file = Path("data/raw/base_stats.json")
    if showdown_file.exists():
        with open(showdown_file, encoding="utf-8") as f:
            return json.load(f)

    # Fallback a pikalytics
    raw_file = Path("data/raw/pikalytics_full.json")
    if not raw_file.exists():
        print(f"⚠️  No existe {showdown_file} ni {raw_file}")
        print(f"    Corre primero: node scripts_fetch_base_stats.js")
        return {}
    with open(raw_file, encoding="utf-8") as f:
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
    """
    Busca stats base de un Pokémon con múltiples fallbacks:
    1. Nombre exacto
    2. Nombre normalizado (Floette-Eternal-Mega → Floette-Mega)
    3. Nombre en minúsculas
    """
    if nombre in STATS_BASE:
        return STATS_BASE[nombre]
    nombre_corto = nombre_valido(nombre)
    if nombre_corto in STATS_BASE:
        return STATS_BASE[nombre_corto]
    if nombre.lower() in STATS_BASE:
        return STATS_BASE[nombre.lower()]
    return {}


def detectar_categoria(nombre: str) -> str:
    """
    Devuelve 'fisico', 'especial' o 'mixto' según los stats base.
    Regla:
      - Si spa > atk + 15 → especial
      - Si atk > spa + 15 → fisico
      - Si similar → mixto
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

        categoria = detectar_categoria(species)

        if categoria == "fisico":
            stat_points = {"HP": 2, "Atk": 32, "Spe": 32}
            nature = "Adamant"
        elif categoria == "especial":
            stat_points = {"HP": 2, "SpA": 32, "Spe": 32}
            nature = "Modest"
        else:
            stats = buscar_stats(species)
            atk = stats.get("atk", 0)
            spa = stats.get("spa", 0)
            if spa >= atk:
                stat_points = {"HP": 2, "SpA": 32, "Spe": 32}
                nature = "Modest"
            else:
                stat_points = {"HP": 2, "Atk": 32, "Spe": 32}
                nature = "Adamant"

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


if __name__ == "__main__":
    print(f"Stats base cargados: {len(STATS_BASE)} Pokémon\n")
    test_pokemon = [
        "Rillaboom", "Sneasler", "Incineroar", "Typhlosion-Hisui",
        "Gholdengo", "Rotom-Wash", "Garchomp", "Salamence",
        "Charizard", "Hydreigon", "Malamar", "Indeedee-F",
        "Gengar-Mega", "Metagross-Mega", "Floette-Eternal-Mega",
    ]
    for nombre in test_pokemon:
        cat = detectar_categoria(nombre)
        stats = buscar_stats(nombre)
        atk = stats.get("atk", "?")
        spa = stats.get("spa", "?")
        spe = stats.get("spe", "?")
        print(f"  {nombre:<25} atk={atk:<4} spa={spa:<4} spe={spe:<4} → {cat}")