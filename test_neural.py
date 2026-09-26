import asyncio
import json
import logging

logging.basicConfig(level=logging.WARNING)

from src.pokemon_set import equipo_a_showdown
from src.neural_player import NeuralPlayer
from src.pokemon_pool import limpiar_equipo

BATTLE_FORMAT = "gen9championsvgc2026regmc"


async def main():
    with open("data/processed/sample_teams.json", encoding="utf-8") as f:
        rivales = json.load(f)

    equipo_1 = limpiar_equipo(rivales[0])
    equipo_2 = limpiar_equipo(rivales[1])

    print(f"Equipo 1: {[p['pokemon'] for p in equipo_1]}")
    print(f"Equipo 2: {[p['pokemon'] for p in equipo_2]}")

    p1 = NeuralPlayer(
        team=equipo_a_showdown(equipo_1),
        battle_format=BATTLE_FORMAT,
        max_concurrent_battles=1,
        accept_open_team_sheet=True,
    )
    p2 = NeuralPlayer(
        team=equipo_a_showdown(equipo_2),
        battle_format=BATTLE_FORMAT,
        max_concurrent_battles=1,
        accept_open_team_sheet=True,
    )

    print("Iniciando batalla...")
    await p1.battle_against(p2, n_battles=1)
    print(f"Terminadas: {p1.n_finished_battles}")
    print(f"Won P1: {p1.n_won_battles}")
    print(f"Won P2: {p2.n_won_battles}")


if __name__ == "__main__":
    asyncio.run(main())