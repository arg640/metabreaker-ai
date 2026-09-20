# src/roles.py
"""
Detección de roles para Pokémon en un equipo.
- Detecta roles según movimientos.
- Verifica COHERENCIA: Trick Room requiere Pokémon lentos, Tailwind requiere rápidos.
"""
from src.pokemon_set import buscar_stats


# ============================================================
# LISTAS DE MOVIMIENTOS
# ============================================================
MOVIMIENTOS_SOPORTE = {
    "Fake Out", "Tailwind", "Trick Room", "Follow Me", "Rage Powder",
    "Helping Hand", "Encore", "Parting Shot", "Spore", "Sleep Powder",
    "Will-O-Wisp", "Taunt", "Quash", "After You", "Ally Switch",
    "Wide Guard", "Quick Guard", "Reflect", "Light Screen",
    "Aurora Veil", "Safeguard", "Coaching", "Decorate", "Life Dew",
    "Skill Swap", "Topsy-Turvy", "Snarl", "Icy Wind",
}

MOVIMIENTOS_SPEED_CONTROL = {
    "Tailwind", "Trick Room", "Icy Wind", "Electroweb", "Quash", "After You",
    "Thunder Wave", "Glare", "Stun Spore", "String Shot",
}

MOVIMIENTOS_RECUPERACION = {
    "Recover", "Slack Off", "Roost", "Synthesis", "Moonlight", "Morning Sun",
    "Soft-Boiled", "Milk Drink", "Shore Up", "Strength Sap", "Leech Seed",
    "Drain Punch", "Giga Drain", "Draining Kiss", "Horn Leech", "Oblivion Wing",
}

MOVIMIENTOS_STATUS = MOVIMIENTOS_SOPORTE | MOVIMIENTOS_RECUPERACION | {
    "Protect", "Detect", "King's Shield", "Spiky Shield", "Baneful Bunker",
    "Obstruct", "Silk Trap", "Burning Bulwark",
    "Swords Dance", "Nasty Plot", "Calm Mind", "Dragon Dance", "Bulk Up",
    "Iron Defense", "Amnesia", "Agility", "Rock Polish", "Shell Smash",
    "Substitute", "Rest", "Sleep Talk", "Toxic", "Toxic Spikes",
    "Stealth Rock", "Spikes", "Sticky Web", "Rain Dance", "Sunny Day",
    "Sandstorm", "Snowscape", "Chilly Reception", "Haze", "Clear Smog",
    "Defog", "Rapid Spin",
}

# Umbrales de velocidad
SPE_LENTO = 70     # <= 70 → abusa de Trick Room
SPE_RAPIDO = 100   # >= 100 → abusa de Tailwind


def es_movimiento_dano(move_name: str) -> bool:
    return move_name not in MOVIMIENTOS_STATUS


def _stats_de(pokemon: dict) -> dict:
    """Devuelve los stats base de un Pokémon."""
    nombre = pokemon.get("pokemon", "")
    return buscar_stats(nombre)


def _speed_de(pokemon: dict) -> int:
    """Devuelve la velocidad base del Pokémon (0 si no se conoce)."""
    return _stats_de(pokemon).get("spe", 0)


def detectar_roles(pokemon: dict) -> set:
    """Devuelve los roles que cumple un Pokémon según sus moves."""
    roles = set()
    moves = {m["name"] for m in pokemon.get("moves", [])}

    if not moves:
        return roles

    if moves & MOVIMIENTOS_SOPORTE:
        roles.add("soporte")

    if moves & MOVIMIENTOS_SPEED_CONTROL:
        roles.add("speed_control")

    tiene_protect = bool(moves & {
        "Protect", "Detect", "King's Shield", "Spiky Shield",
        "Baneful Bunker", "Obstruct",
    })
    tiene_recuperacion = bool(moves & MOVIMIENTOS_RECUPERACION)
    if tiene_protect and tiene_recuperacion:
        roles.add("tanque")

    n_dano = sum(1 for m in moves if es_movimiento_dano(m))
    if n_dano >= 3:
        roles.add("atacante")

    return roles


def score_roles(equipo: list) -> float:
    """
    Score de 0 a 1 según distribución y COHERENCIA de roles.
    Verifica que TR/Tailwind tengan sentido con los stats del equipo.
    """
    conteos = {"soporte": 0, "speed_control": 0, "tanque": 0, "atacante": 0}
    for p in equipo:
        for rol in detectar_roles(p):
            conteos[rol] += 1

    # Contar Pokémon lentos y rápidos
    speeds = [_speed_de(p) for p in equipo]
    n_lentos = sum(1 for s in speeds if 0 < s <= SPE_LENTO)
    n_rapidos = sum(1 for s in speeds if s >= SPE_RAPIDO)

    # ¿Qué speed control tiene el equipo?
    todos_los_moves = set()
    for p in equipo:
        for m in p.get("moves", []):
            todos_los_moves.add(m["name"])

    tiene_tr = "Trick Room" in todos_los_moves
    tiene_tw = "Tailwind" in todos_los_moves

    score = 1.0

    # --- Reglas generales de roles ---
    if conteos["atacante"] < 2:
        score -= 0.25
    if conteos["atacante"] > 5:
        score -= 0.15
    if conteos["soporte"] == 0:
        score -= 0.20
    elif conteos["soporte"] > 3:
        score -= 0.15
    if conteos["tanque"] == 0:
        score -= 0.15

    # --- Coherencia del speed control ---
    if not tiene_tr and not tiene_tw:
        score -= 0.35
    else:
        if tiene_tr and n_lentos < 2:
            score -= 0.20
        if tiene_tw and n_rapidos < 2:
            score -= 0.15

    return max(0.0, score)


if __name__ == "__main__":
    import json

    with open("data/processed/sample_teams.json", encoding="utf-8") as f:
        equipos = json.load(f)

    for i, eq in enumerate(equipos[:5]):
        print(f"\nEquipo {i+1}:")
        for p in eq:
            sp = _speed_de(p)
            roles = detectar_roles(p)
            print(f"  {p['pokemon']:<25} spe={sp:<4} roles={roles}")
        print(f"  SCORE: {score_roles(eq):.3f}")