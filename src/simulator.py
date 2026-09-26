# src/simulator.py
"""
Simulador de batallas reutilizable para el algoritmo genético.
Usa NeuralPlayer (Behavior Cloning) para tomar decisiones como humano.
"""
import asyncio
import logging

from src.pokemon_set import equipo_a_showdown
from src.neural_player import NeuralPlayer
from src.pokemon_pool import limpiar_equipo

logging.getLogger("poke_env").setLevel(logging.ERROR)
logging.getLogger("NeuralPlayer").setLevel(logging.ERROR)

BATTLE_FORMAT = "gen9championsvgc2026regmc"


async def _simular_async(
    equipo_1: list[dict],
    equipo_2: list[dict],
    n_batallas: int = 1,
) -> float:
    """Corre n_batallas entre equipo_1 y equipo_2. Devuelve el winrate de equipo_1."""

    # Limpiar AMBOS equipos (corrige habilidades, Species Clause, Item Clause)
    equipo_1 = limpiar_equipo(equipo_1)
    equipo_2 = limpiar_equipo(equipo_2)

    # Si por alguna razón un equipo no tiene 6 Pokémon, fitness 0
    if len(equipo_1) < 6 or len(equipo_2) < 6:
        return 0.0

    equipo_1_txt = equipo_a_showdown(equipo_1)
    equipo_2_txt = equipo_a_showdown(equipo_2)

    # max_concurrent_battles=1 para evitar conflictos de OTS en el servidor
    player_1 = NeuralPlayer(
        team=equipo_1_txt,
        battle_format=BATTLE_FORMAT,
        max_concurrent_battles=1,
        accept_open_team_sheet=True,
    )
    player_2 = NeuralPlayer(
        team=equipo_2_txt,
        battle_format=BATTLE_FORMAT,
        max_concurrent_battles=1,
        accept_open_team_sheet=True,
    )

    await player_1.battle_against(player_2, n_battles=n_batallas)

    if player_1.n_finished_battles == 0:
        return 0.0
    return player_1.n_won_battles / player_1.n_finished_battles


def simular_enfrentamiento(
    equipo_1: list[dict],
    equipo_2: list[dict],
    n_batallas: int = 1,
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

    winrate = simular_enfrentamiento(equipos[0], equipos[1], n_batallas=3)
    print(f"Winrate del Equipo 1 vs Equipo 2 (3 batallas): {winrate:.1%}")