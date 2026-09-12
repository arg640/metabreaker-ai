# src/type_chart.py
"""
Tabla de efectividad de tipos de Pokémon (Gen 6+).
CHART[ataque][defensa] = multiplicador
"""

TYPES = [
    "normal", "fire", "water", "electric", "grass", "ice",
    "fighting", "poison", "ground", "flying", "psychic", "bug",
    "rock", "ghost", "dragon", "dark", "steel", "fairy",
]

# Valores por defecto: 1.0 (efectividad normal)
CHART: dict[str, dict[str, float]] = {a: {d: 1.0 for d in TYPES} for a in TYPES}


def _set(atk: str, defensas: dict[str, float]) -> None:
    for d, mult in defensas.items():
        CHART[atk][d] = mult


# Normal
_set("normal", {"rock": 0.5, "steel": 0.5, "ghost": 0.0})
# Fire
_set("fire", {
    "fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0,
    "bug": 2.0, "rock": 0.5, "dragon": 0.5, "steel": 2.0,
})
# Water
_set("water", {
    "fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0,
    "rock": 2.0, "dragon": 0.5,
})
# Electric
_set("electric", {
    "water": 2.0, "electric": 0.5, "grass": 0.5, "flying": 2.0,
    "ground": 0.0, "dragon": 0.5,
})
# Grass
_set("grass", {
    "fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5,
    "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0,
    "dragon": 0.5, "steel": 0.5,
})
# Ice
_set("ice", {
    "fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 0.5,
    "ground": 2.0, "flying": 2.0, "dragon": 2.0, "steel": 0.5,
})
# Fighting
_set("fighting", {
    "normal": 2.0, "ice": 2.0, "poison": 0.5, "flying": 0.5,
    "psychic": 0.5, "bug": 0.5, "rock": 2.0, "ghost": 0.0,
    "dark": 2.0, "steel": 2.0, "fairy": 0.5,
})
# Poison
_set("poison", {
    "grass": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5,
    "ghost": 0.5, "steel": 0.0, "fairy": 2.0,
})
# Ground
_set("ground", {
    "fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0,
    "flying": 0.0, "bug": 0.5, "rock": 2.0, "steel": 2.0,
})
# Flying
_set("flying", {
    "electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0,
    "rock": 0.5, "steel": 0.5,
})
# Psychic
_set("psychic", {
    "fighting": 2.0, "poison": 2.0, "psychic": 0.5,
    "dark": 0.0, "steel": 0.5,
})
# Bug
_set("bug", {
    "fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 0.5,
    "flying": 0.5, "psychic": 2.0, "ghost": 0.5, "dark": 2.0,
    "steel": 0.5, "fairy": 0.5,
})
# Rock
_set("rock", {
    "fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5,
    "flying": 2.0, "bug": 2.0, "steel": 0.5,
})
# Ghost
_set("ghost", {
    "normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5,
})
# Dragon
_set("dragon", {"dragon": 2.0, "steel": 0.5, "fairy": 0.0})
# Dark
_set("dark", {
    "fighting": 0.5, "psychic": 2.0, "ghost": 2.0,
    "dark": 0.5, "fairy": 0.5,
})
# Steel
_set("steel", {
    "fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2.0,
    "rock": 2.0, "steel": 0.5, "fairy": 2.0,
})
# Fairy
_set("fairy", {
    "fire": 0.5, "fighting": 2.0, "poison": 0.5, "dragon": 2.0,
    "dark": 2.0, "steel": 0.5,
})


def multiplicador(ataque: str, tipos_defensa: list[str]) -> float:
    """Devuelve el multiplicador total de un ataque contra 1 o 2 tipos defensivos."""
    mult = 1.0
    for t in tipos_defensa:
        mult *= CHART[ataque.lower()][t.lower()]
    return mult


def debilidades(tipos_defensa: list[str], umbral: float = 2.0) -> dict[str, float]:
    """Devuelve los tipos de ataque contra los que este Pokémon es débil (mult >= umbral)."""
    return {
        atk: multiplicador(atk, tipos_defensa)
        for atk in TYPES
        if multiplicador(atk, tipos_defensa) >= umbral
    }