# scripts/analyze_winner_logs.py
"""
Analiza los pares (estado, acción) capturados por el GA durante la corrida.

Uso:
    python -m scripts.analyze_winner_logs
"""
from collections import Counter

import numpy as np
import torch

from src.config import (
    HUMAN_LOGS_PATH,
    MAX_ACTIONS,
    MAX_SPECIES,
    MODEL_PATH,
    N_FIXED,
    WINNER_LOGS,
)


def _state_key(feats, max_species: int, n_fixed: int):
    feats_np = np.asarray(feats, dtype=np.float32)
    turn = int(feats_np[0] * 20)
    s_p1a = int(feats_np[n_fixed:n_fixed + max_species].argmax())
    s_p1b = int(feats_np[n_fixed + max_species:n_fixed + max_species * 2].argmax())
    return (turn, s_p1a, s_p1b)


def main():
    if not MODEL_PATH.exists():
        print(f"[ERROR] No existe {MODEL_PATH}. Entrená primero con:")
        print("   python -m scripts.bc_train")
        return
    if not WINNER_LOGS.exists():
        print(f"[ERROR] No existe {WINNER_LOGS}. Corré el GA al menos una vez.")
        return

    print("[LOAD] Cargando modelo para mapear índices de movimientos...")
    ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    move_vocab = ckpt["move_vocab"]
    idx_to_move = {v: k for k, v in move_vocab.items()}

    print("[LOAD] Cargando winner_logs...")
    states, actions = [], []
    with WINNER_LOGS.open(encoding="utf-8") as f:
        for line in f:
            d = __import__("json").loads(line)
            states.append(d["f"])
            actions.append(d["a"])

    print(f"Total pares: {len(actions)}\n")

    # ============================================================
    print("=" * 60)
    print("TOP 20 MOVIMIENTOS ELEGIDOS POR EL MODELO")
    print("=" * 60)
    action_counter = Counter(actions)
    for idx, count in action_counter.most_common(20):
        move_name = idx_to_move.get(idx, f"??? ({idx})")
        pct = count / len(actions) * 100
        bar = "█" * int(pct / 2)
        print(f"  {move_name:<20} {count:>6} ({pct:>5.1f}%) {bar}")

    top10_pct = sum(c for _, c in action_counter.most_common(10)) / len(actions) * 100
    print(f"\n[STATS] Top 10 moves concentran el {top10_pct:.1f}% de las acciones")
    print(f"[STATS] Moves distintos usados: {len(action_counter)}/{MAX_ACTIONS}")

    # ============================================================
    print("\n" + "=" * 60)
    print("ANÁLISIS DE CONCENTRACIÓN POR ESTADO")
    print("=" * 60)

    state_groups: dict = {}
    for feats, action in zip(states, actions):
        key = _state_key(feats, MAX_SPECIES, N_FIXED)
        state_groups.setdefault(key, []).append(action)

    grupos_triviales = 0
    for acts in state_groups.values():
        if len(acts) < 3:
            continue
        top_count = Counter(acts).most_common(1)[0][1]
        if top_count / len(acts) > 0.8:
            grupos_triviales += 1

    print(f"Grupos totales de estados similares: {len(state_groups)}")
    print(f"Grupos con >80% de un solo move: {grupos_triviales}")

    # ============================================================
    print("\n" + "=" * 60)
    print("COMPARACIÓN CON HUMANOS")
    print("=" * 60)

    if not HUMAN_LOGS_PATH.exists():
        print(f"[WARN]  No existe {HUMAN_LOGS_PATH}, saltando comparación.")
        return

    import json
    human_actions = []
    with HUMAN_LOGS_PATH.open(encoding="utf-8") as f:
        logs = json.load(f)
    for i, (_, (_, log)) in enumerate(logs.items()):
        if i > 3000:
            break
        for line in log.split("\n"):
            if line.startswith("|move|p1"):
                parts = line.split("|")
                if len(parts) > 3:
                    move_name = (
                        parts[3].strip().lower()
                        .replace(" ", "").replace("-", "").replace("'", "")
                    )
                    idx = move_vocab.get(move_name, -1)
                    if idx >= 0:
                        human_actions.append(idx)

    human_counter = Counter(human_actions)
    print(f"Total acciones humanas (muestra): {len(human_actions)}\n")
    print("  Move         | Humano %  | Modelo %  | Ratio")
    print("  " + "-" * 55)
    for idx, count in action_counter.most_common(15):
        move_name = idx_to_move.get(idx, f"??? ({idx})")
        h_pct = human_counter.get(idx, 0) / max(1, len(human_actions)) * 100
        m_pct = count / len(actions) * 100
        ratio = m_pct / max(0.01, h_pct)
        marker = "" if ratio > 3 else ""
        print(f"  {move_name:<12} | {h_pct:>7.2f}  | {m_pct:>7.2f}  | {ratio:>5.2f} {marker}")


if __name__ == "__main__":
    main()