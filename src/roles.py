# src/roles.py
"""
Detección de roles para Pokémon en un equipo.
Se basa en los movimientos del Pokémon (no en stats).
"""

MOVIMIENTOS_SOPORTE = {
    "Fake Out", "Tailwind", "Trick Room", "Follow Me", "Rage Powder",
    "Helping Hand", "Encore", "Parting Shot", "Spore", "Sleep Powder",
    "Will-O-Wisp", "Taunt", "Quash", "After You", "Ally Switch",
    "Wide Guard", "Quick Guard", "Reflect", "Light Screen",
    "Aurora Veil", "Safeguard", "Coaching", "Decorate", "Life Dew",
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


def es_movimiento_dano(move_name: str) -> bool:
    return move_name not in MOVIMIENTOS_STATUS


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
    Score de 0 a 1 según distribución de roles.
    Ideal: 3-4 atacantes, 1-2 soportes, 1 tanque, 1+ speed control.
    """
    conteos = {"soporte": 0, "speed_control": 0, "tanque": 0, "atacante": 0}
    for p in equipo:
        for rol in detectar_roles(p):
            conteos[rol] += 1

    score = 1.0
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
    if conteos["speed_control"] == 0:
        score -= 0.35

    return max(0.0, score)


if __name__ == "__main__":
    # Prueba rápida con algunos equipos
    import json

    with open("data/processed/sample_teams.json", encoding="utf-8") as f:
        equipos = json.load(f)

    for i, eq in enumerate(equipos[:3]):
        print(f"\nEquipo {i+1}:")
        for p in eq:
            print(f"  {p['pokemon']:<20} roles={detectar_roles(p)}")
        print(f"  SCORE: {score_roles(eq):.3f}")