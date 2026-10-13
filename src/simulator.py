# src/simulator.py
"""
Simulador de batallas con event loop PERSISTENTE y batallas paralelas.

Motivación:
- La versión anterior llamaba asyncio.run() por cada enfrentamiento. Eso crea
  un event loop nuevo + 2 websockets nuevos por llamada. En una corrida de GA
  con miles de batallas, eso es brutalmente lento y frágil (de ahí el watchdog).
- Ahora hay un loop vivo durante toda la corrida, y se lanzan N batallas en
  paralelo con asyncio.gather().

Uso típico en el GA:
    arena = BattleArena(n_parallel=3)
    try:
        wr = arena.battle(equipo_a, equipo_b, n_batallas=4,
                          model_a=MODEL_PATH, model_b=MODEL_PATH_2)
    finally:
        arena.close()

Compatibilidad:
- `simular_enfrentamiento(...)` sigue existiendo, usa una arena global lazy.
"""
import asyncio
import logging
from typing import Optional

from src.config import (
    BATTLE_FORMAT,
    MAX_CONCURRENT_BATTLES,
    MODEL_PATH,
    MODEL_PATH_2,
)
from src.neural_player import NeuralPlayer
from src.pokemon_pool import limpiar_equipo
from src.pokemon_set import equipo_a_showdown

logging.getLogger("poke_env").setLevel(logging.ERROR)
logging.getLogger("NeuralPlayer").setLevel(logging.ERROR)


def _split_evenly(n: int, k: int) -> list[int]:
    """Reparte n batallas en k workers de la forma más pareja posible."""
    if k <= 0:
        return []
    base, resto = divmod(n, k)
    return [base + (1 if i < resto else 0) for i in range(k)]


class BattleArena:
    """
    Arena persistente. Mantiene un event loop vivo durante toda la corrida
    del GA para evitar recrear loop + websockets en cada llamada.
    """

    def __init__(self, n_parallel: int = MAX_CONCURRENT_BATTLES):
        self.n_parallel = max(1, int(n_parallel))
        self._loop = asyncio.new_event_loop()
        self._closed = False

    # ------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------
    def battle(
        self,
        equipo_1: list[dict],
        equipo_2: list[dict],
        n_batallas: int = 1,
        model_a: Optional[str] = None,
        model_b: Optional[str] = None,
    ) -> float:
        """
        Corre n_batallas entre equipo_1 (agente A) y equipo_2 (agente B).
        Devuelve el winrate de equipo_1 (0.0 a 1.0).

        - model_a / model_b: rutas a checkpoints .pt distintos.
          Si no se pasan, se usa MODEL_PATH para ambos.
          En el GA conviene pasar MODEL_PATH y MODEL_PATH_2 (agentes
          independientes) para no medir "self-play".
        """
        if self._closed:
            raise RuntimeError("BattleArena ya fue cerrada.")

        return self._loop.run_until_complete(
            self._battle_async(equipo_1, equipo_2, n_batallas, model_a, model_b)
        )

    def close(self) -> None:
        """Cierra el event loop. Llamar SIEMPRE al final de la corrida."""
        if self._closed:
            return
        try:
            # Dar chance a tareas pendientes (websockets) de cerrar limpio.
            self._loop.run_until_complete(asyncio.sleep(0.05))
        except Exception:
            pass
        self._loop.close()
        self._closed = True

    # ------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------
    async def _battle_async(
        self,
        equipo_1: list[dict],
        equipo_2: list[dict],
        n_batallas: int,
        model_a: Optional[str],
        model_b: Optional[str],
    ) -> float:
        # Limpieza: Species Clause + Item Clause + habilidades válidas
        equipo_1 = limpiar_equipo(equipo_1)
        equipo_2 = limpiar_equipo(equipo_2)

        if len(equipo_1) < 6 or len(equipo_2) < 6:
            return 0.0

        t1 = equipo_a_showdown(equipo_1)
        t2 = equipo_a_showdown(equipo_2)

        # Repartir n_batallas entre workers paralelos
        n_workers = min(self.n_parallel, n_batallas)
        batches = _split_evenly(n_batallas, n_workers)

        async def worker(batch_size: int):
            p1 = NeuralPlayer(
                team=t1,
                battle_format=BATTLE_FORMAT,
                max_concurrent_battles=1,
                accept_open_team_sheet=False,
                model_path=model_a or MODEL_PATH,
            )
            p2 = NeuralPlayer(
                team=t2,
                battle_format=BATTLE_FORMAT,
                max_concurrent_battles=1,
                accept_open_team_sheet=False,
                model_path=model_b or MODEL_PATH,
            )
            try:
                await p1.battle_against(p2, n_battles=batch_size)
                return p1.n_won_battles, p1.n_finished_battles
            except Exception:
                return 0, 0
            finally:
                del p1, p2

        resultados = await asyncio.gather(
            *[worker(b) for b in batches if b > 0],
            return_exceptions=False,
        )

        ganadas = sum(r[0] for r in resultados)
        total = sum(r[1] for r in resultados)
        return (ganadas / total) if total > 0 else 0.0


# ------------------------------------------------------------
# Wrapper de compatibilidad (API vieja)
# ------------------------------------------------------------
_ARENA_SINGLETON: Optional[BattleArena] = None


def simular_enfrentamiento(
    equipo_1: list[dict],
    equipo_2: list[dict],
    n_batallas: int = 1,
) -> float:
    """
    Wrapper de compatibilidad. Crea (o reusa) una arena global lazy.
    Para corridas largas usá BattleArena directamente y cerrala al final.
    """
    global _ARENA_SINGLETON
    if _ARENA_SINGLETON is None or _ARENA_SINGLETON._closed:
        _ARENA_SINGLETON = BattleArena()
    return _ARENA_SINGLETON.battle(equipo_1, equipo_2, n_batallas)


# ------------------------------------------------------------
# Test rápido
# ------------------------------------------------------------
if __name__ == "__main__":
    import json
    from src.config import SAMPLE_TEAMS_FILE

    with open(SAMPLE_TEAMS_FILE, encoding="utf-8") as f:
        equipos = json.load(f)

    arena = BattleArena(n_parallel=2)
    try:
        wr = arena.battle(
            equipos[0], equipos[1], n_batallas=4,
            model_a=str(MODEL_PATH), model_b=str(MODEL_PATH_2),
        )
        print(f"Winrate Equipo 1 vs Equipo 2 (4 batallas, paralelo): {wr:.1%}")
    finally:
        arena.close()