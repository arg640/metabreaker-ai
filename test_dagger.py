import asyncio
import json
from pathlib import Path

from src.pokemon_set import equipo_a_showdown
from src.neural_player import NeuralPlayer
from src.pokemon_pool import limpiar_equipo

BATTLE_FORMAT = "gen9championsvgc2026regmc"
LOG_FILE = Path("data/ga_logs/winner_logs.jsonl")


async def main():
    if LOG_FILE.exists():
        LOG_FILE.unlink()
        print("Logs previos eliminados")

    with open("data/processed/sample_teams.json", encoding="utf-8") as f:
        rivales = json.load(f)

    equipo_1 = limpiar_equipo(rivales[0])
    equipo_2 = limpiar_equipo(rivales[1])

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

    print("Iniciando 1 batalla...")
    await p1.battle_against(p2, n_battles=1)

    print(f"\nP1 ganó: {p1.n_won_battles} | P2 ganó: {p2.n_won_battles}")

    if LOG_FILE.exists():
        with LOG_FILE.open(encoding="utf-8") as f:
            n = sum(1 for _ in f)
        print(f"✅ Logs capturados: {n} registros")
    else:
        print("❌ No se creó archivo de logs")


if __name__ == "__main__":
    asyncio.run(main())