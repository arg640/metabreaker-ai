# src/pokemon_set.py
"""
Representa un PokemonSet individual y sabe convertirse al formato
'export' de Pokemon Showdown para el formato Champions.
"""
from dataclasses import dataclass, field
from typing import Optional


# En Champions, los Stat Points van de 0 a 32 por stat, con un máximo total de 66.
# Heurística simple: máximo en el stat ofensivo principal + máximo en Speed + 2 en HP.
FISICOS_COMUNES = {
    "Rillaboom", "Sneasler", "Incineroar", "Salamence-Mega", "Kingambit",
    "Basculegion", "Golisopod-Mega", "Garchomp", "Tyranitar", "Baxcalibur",
    "Lucario", "Arcanine-Hisui", "Raichu-Mega-Y", "Metagross-Mega",
}

ESPECIALES_COMUNES = {
    "Gholdengo", "Floette-Mega", "Floette-Eternal-Mega", "Sinistcha",
    "Archaludon", "Charizard-Mega-Y", "Froslass-Mega", "Indeedee",
    "Indeedee-F", "Milotic", "Pelipper", "Whimsicott", "Sylveon",
    "Farigiraf", "Torkoal",
}

# Nombres de especie demasiado largos para Showdown (> 18 caracteres).
# Mapea el nombre de Pikalytics al nombre corto que acepta el servidor.
NOMBRES_CORTOS = {
    "Floette-Eternal-Mega": "Floette-Mega",
    "Floette-Eternal": "Floette-Mega",
}


def nombre_valido(nombre: str) -> str:
    """Devuelve un nombre de especie aceptado por Showdown (≤ 18 caracteres)."""
    if nombre in NOMBRES_CORTOS:
        return NOMBRES_CORTOS[nombre]
    if len(nombre) > 18:
        # Truncar como último recurso (no debería pasar tras el mapeo)
        return nombre[:18]
    return nombre


@dataclass
class PokemonSet:
    species: str
    moves: list[str]
    item: str = ""
    ability: str = ""
    level: int = 50
    nature: str = "Serious"
    stat_points: dict[str, int] = field(default_factory=dict)  # Stat Points de Champions
    tera_type: Optional[str] = None

    def to_showdown(self) -> str:
        """Convierte este PokemonSet al formato export de Showdown."""
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

        # EVs: en Champions los EVs son los Stat Points (0-32 cada uno, máximo 66 total)
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
        """Construye un PokemonSet desde el dict del sample_teams.json."""
        species = data["pokemon"]
        moves = [m["name"] for m in data.get("moves", []) if m.get("name")]

        # Stat Points según heurística: 32 en ataque principal + 32 en Speed + 2 en HP = 66
        if species in FISICOS_COMUNES:
            stat_points = {"HP": 2, "Atk": 32, "Spe": 32}
            nature = "Adamant"
        elif species in ESPECIALES_COMUNES:
            stat_points = {"HP": 2, "SpA": 32, "Spe": 32}
            nature = "Modest"
        else:
            stat_points = {"HP": 32, "Atk": 32, "Spe": 2}
            nature = "Serious"

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
    """Convierte una lista de dicts (un equipo del JSON) al formato export de Showdown."""
    sets = [PokemonSet.from_dict(p) for p in equipo]
    return "\n\n".join(s.to_showdown() for s in sets)