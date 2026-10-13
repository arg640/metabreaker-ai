# src/roles.py
"""
Detección de roles para Pokémon en un equipo.

- Detecta roles según movimientos.
- Verifica COHERENCIA: Trick Room requiere Pokémon lentos, Tailwind rápidos.
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
    "Skill Swap", "Topsy-Turvy", "Snarl", "Icy Wind", "Super Fang",
    "Heal Pulse", "Jungle Healing", "Chilly Reception",
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

MOVIMIENTOS_PROTECT = {
    "Protect", "Detect", "King's Shield", "Spiky Shield", "Baneful Bunker",
    "Obstruct", "Silk Trap", "Burning Bulwark",
}

MOVIMIENTOS_STATUS = (
    MOVIMIENTOS_SOPORTE
    | MOVIMIENTOS_RECUPERACION
    | MOVIMIENTOS_PROTECT
    | {
        "Swords Dance", "Nasty Plot", "Calm Mind", "Dragon Dance", "Bulk Up",
        "Iron Defense", "Amnesia", "Agility", "Rock Polish", "Shell Smash",
        "Substitute", "Rest", "Sleep Talk", "Toxic", "Toxic Spikes",
        "Stealth Rock", "Spikes", "Sticky Web", "Rain Dance", "Sunny Day",
        "Sandstorm", "Snowscape", "Haze", "Clear Smog", "Defog", "Rapid Spin",
    }
)

# Umbrales de velocidad (base stat de Velocidad)
SPE_LENTO = 60     # <= 60 -> TR real
SPE_RAPIDO = 100   # >= 100 -> Tailwind real

# Movimientos que están en listas de soporte/recuperación pero SÍ hacen daño.
# Sin esto, atacantes híbridos como Incineroar o Iron Hands no se detectan.
MOVIMIENTOS_DANO_HIBRIDO = {
    "Fake Out", "Icy Wind", "Snarl", "Electroweb", "Super Fang",
    "Drain Punch", "Giga Drain", "Draining Kiss", "Horn Leech", "Oblivion Wing",
}


def es_movimiento_dano(move_name: str) -> bool:
    if move_name in MOVIMIENTOS_DANO_HIBRIDO:
        return True
    return move_name not in MOVIMIENTOS_STATUS

def _stats_de(pokemon: dict) -> dict:
    return buscar_stats(pokemon.get("pokemon", ""))


def _speed_de(pokemon: dict) -> int:
    return _stats_de(pokemon).get("spe", 0)


def detectar_roles(pokemon: dict) -> set:
    roles: set[str] = set()
    moves = {m["name"] for m in pokemon.get("moves", [])}

    if not moves:
        return roles

    if moves & MOVIMIENTOS_SOPORTE:
        roles.add("soporte")

    if moves & MOVIMIENTOS_SPEED_CONTROL:
        roles.add("speed_control")

    tiene_protect = bool(moves & MOVIMIENTOS_PROTECT)
    tiene_recuperacion = bool(moves & MOVIMIENTOS_RECUPERACION)
    if tiene_protect and tiene_recuperacion:
        roles.add("tanque")

    n_dano = sum(1 for m in moves if es_movimiento_dano(m))
    if n_dano >= 3:
        roles.add("atacante")

    return roles


def score_roles(equipo: list) -> float:
    """
    Score 0..1 según distribución y coherencia de roles en el equipo.
    """
    conteos = {"soporte": 0, "speed_control": 0, "tanque": 0, "atacante": 0}
    for p in equipo:
        for rol in detectar_roles(p):
            conteos[rol] += 1

    speeds = [_speed_de(p) for p in equipo]
    n_lentos = sum(1 for s in speeds if 0 < s <= SPE_LENTO)
    n_rapidos = sum(1 for s in speeds if s >= SPE_RAPIDO)

    todos_los_moves: set[str] = set()
    for p in equipo:
        for m in p.get("moves", []):
            todos_los_moves.add(m["name"])

    tiene_tr = "Trick Room" in todos_los_moves
    tiene_tw = "Tailwind" in todos_los_moves

    score = 1.0

    # Roles generales
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

    # Coherencia del speed control
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
    from src.config import SAMPLE_TEAMS_FILE

    with open(SAMPLE_TEAMS_FILE, encoding="utf-8") as f:
        equipos = json.load(f)

    for i, eq in enumerate(equipos[:5]):
        print(f"\nEquipo {i+1}:")
        for p in eq:
            sp = _speed_de(p)
            roles = detectar_roles(p)
            print(f"  {p['pokemon']:<25} spe={sp:<4} roles={roles}")
        print(f"  SCORE: {score_roles(eq):.3f}")