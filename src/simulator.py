# src/simulator.py
"""
Simulador de batallas reutilizable para el algoritmo genético.
Expone una función `simular_enfrentamiento` que devuelve el winrate
del equipo 1 contra el equipo 2 en N batallas.
"""
import asyncio
import logging

from src.pokemon_set import equipo_a_showdown
from src.team_player import TeamPlayer

# Silencia los warnings de poke-env (Open Team Sheets, popups, etc.)
logging.getLogger("poke_env").setLevel(logging.ERROR)
logging.getLogger("TeamPlayer").setLevel(logging.ERROR)

BATTLE_FORMAT = "gen9championsvgc2026regmc"

# Items de respaldo para cuando hay duplicados (Item Clause)
ITEMS_RESPALDO = [
    "Sitrus Berry",
    "Focus Sash",
    "Choice Scarf",
    "Leftovers",
    "Life Orb",
    "Miracle Seed",
    "Light Clay",
    "Rocky Helmet",
    "Grassy Seed",
    "Psychic Seed",
    "White Herb",
    "Eject Button",
    "Black Glasses",
    "Charcoal",
    "Mystic Water",
    "Fairy Feather",
    "Chople Berry",
    "Colbur Berry",
    "Passho Berry",
]


def reparar_items_duplicados(equipo: list[dict]) -> list[dict]:
    """
    Repara un equipo para cumplir con la Item Clause de VGC.
    Si dos Pokémon comparten el mismo item, el segundo (y siguientes) reciben
    un item de respaldo que no esté ya en uso.
    Devuelve una copia del equipo (no modifica el original).
    """
    equipo_reparado = [dict(p) for p in equipo]  # copia superficial
    items_usados = set()

    for p in equipo_reparado:
        item = p.get("item") or ""
        if item and item in items_usados:
            # Busca un item de respaldo libre
            for candidato in ITEMS_RESPALDO:
                if candidato not in items_usados:
                    p["item"] = candidato
                    items_usados.add(candidato)
                    break
            else:
                # Si no hay respaldo, quita el item
                p["item"] = ""
        else:
            if item:
                items_usados.add(item)

    return equipo_reparado


async def _simular_async(
    equipo_1: list[dict],
    equipo_2: list[dict],
    n_batallas: int = 3,
) -> float:
    """Corre n_batallas batallas entre equipo_1 y equipo_2. Devuelve el winrate de equipo_1."""
    # Reparar items antes de convertir a formato Showdown
    equipo_1 = reparar_items_duplicados(equipo_1)
    equipo_2 = reparar_items_duplicados(equipo_2)

    equipo_1_txt = equipo_a_showdown(equipo_1)
    equipo_2_txt = equipo_a_showdown(equipo_2)

    player_1 = TeamPlayer(
        team=equipo_1_txt,
        battle_format=BATTLE_FORMAT,
        max_concurrent_battles=n_batallas,
        accept_open_team_sheet=True,
    )
    player_2 = TeamPlayer(
        team=equipo_2_txt,
        battle_format=BATTLE_FORMAT,
        max_concurrent_battles=n_batallas,
        accept_open_team_sheet=True,
    )

    await player_1.battle_against(player_2, n_battles=n_batallas)

    if player_1.n_finished_battles == 0:
        return 0.0
    return player_1.n_won_battles / player_1.n_finished_battles


def simular_enfrentamiento(
    equipo_1: list[dict],
    equipo_2: list[dict],
    n_batallas: int = 3,
) -> float:
    """
    Envoltorio síncrono de _simular_async.
    Devuelve el winrate del equipo_1 contra el equipo_2 (0.0 a 1.0).
    """
    return asyncio.run(_simular_async(equipo_1, equipo_2, n_batallas))


if __name__ == "__main__":
    import json

    with open("data/processed/sample_teams.json", encoding="utf-8") as f:
        equipos = json.load(f)

    winrate = simular_enfrentamiento(equipos[0], equipos[1], n_batallas=5)
    print(f"Winrate del Equipo 1 vs Equipo 2 (5 batallas): {winrate:.1%}")