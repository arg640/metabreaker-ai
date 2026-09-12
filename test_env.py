# test_env.py
import asyncio
from poke_env.player import RandomPlayer

async def main():
    # Crea dos jugadores aleatorios
    player_1 = RandomPlayer(max_concurrent_battles=1)
    player_2 = RandomPlayer(max_concurrent_battles=1)

    # Haz que luchen una vez
    await player_1.battle_against(player_2, n_battles=1)

    # Muestra los resultados
    print(f"Batallas terminadas: {player_1.n_finished_battles}")
    print(f"Victorias del Jugador 1: {player_1.n_won_battles}")

if __name__ == "__main__":
    asyncio.run(main())