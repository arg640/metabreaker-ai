"""Analiza los pares (estado, acción) capturados por el GA."""
import json
from collections import Counter
from pathlib import Path

import numpy as np
import torch

LOGS_PATH = Path("data/ga_logs/winner_logs.jsonl")
MODEL_PATH = Path("models_bc/bc_model.pt")

MAX_SPECIES = 100
MAX_ACTIONS = 150
N_FIXED = 28
N_SPECIES_BLOCK = MAX_SPECIES * 4
N_MOVES_BLOCK = MAX_ACTIONS
N_COUNT_BLOCK = 4
N_FEATURES = N_FIXED + N_SPECIES_BLOCK + N_MOVES_BLOCK + N_COUNT_BLOCK


def main():
    print("📂 Cargando modelo para mapear índices de movimientos...")
    ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    move_vocab = ckpt["move_vocab"]
    idx_to_move = {v: k for k, v in move_vocab.items()}
    species_vocab = ckpt["species_vocab"]

    print("📂 Cargando winner_logs...")
    states = []
    actions = []
    with LOGS_PATH.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            states.append(d["f"])
            actions.append(d["a"])

    print(f"Total pares: {len(actions)}")

    # Distribución de acciones
    print("\n" + "=" * 60)
    print("TOP 20 MOVIMIENTOS ELEGIDOS POR EL MODELO")
    print("=" * 60)
    action_counter = Counter(actions)
    for idx, count in action_counter.most_common(20):
        move_name = idx_to_move.get(idx, f"??? ({idx})")
        pct = count / len(actions) * 100
        bar = "█" * int(pct / 2)
        print(f"  {move_name:<20} {count:>6} ({pct:>5.1f}%) {bar}")

    # Concentración
    top10_pct = sum(c for _, c in action_counter.most_common(10)) / len(actions) * 100
    print(f"\n📊 Top 10 moves concentran el {top10_pct:.1f}% de las acciones")

    # Cuántos moves distintos usa
    n_distintos = len(action_counter)
    print(f"📊 Moves distintos usados: {n_distintos}/150")

    # Análisis de "trivialidad": ¿hay estados donde siempre elige lo mismo?
    print("\n" + "=" * 60)
    print("ANÁLISIS DE CONCENTRACIÓN POR ESTADO")
    print("=" * 60)

    # Agrupar estados por "hash" (turn + species + HP)
    X = np.array(states, dtype=np.float32)

    # Clave: species activas + turn (redondeado)
    def state_key(feats):
        feats_np = np.array(feats, dtype=np.float32)
        turn = int(feats_np[0] * 20)
        s_p1a = int(feats_np[N_FIXED:N_FIXED + MAX_SPECIES].argmax())
        s_p1b = int(feats_np[N_FIXED + MAX_SPECIES:N_FIXED + MAX_SPECIES * 2].argmax())
        return (turn, s_p1a, s_p1b)

    state_groups = {}
    for feats, action in zip(states, actions):
        key = state_key(feats)
        if key not in state_groups:
            state_groups[key] = []
        state_groups[key].append(action)

    # Contar cuántos grupos tienen >80% de un mismo move
    grupos_triviales = 0
    for key, acts in state_groups.items():
        if len(acts) < 3:
            continue
        top_count = Counter(acts).most_common(1)[0][1]
        if top_count / len(acts) > 0.8:
            grupos_triviales += 1

    print(f"Grupos totales de estados similares: {len(state_groups)}")
    print(f"Grupos con >80% de un solo move: {grupos_triviales}")

    # Comparar contra distribución humana (los 15k replays)
    print("\n" + "=" * 60)
    print("COMPARACIÓN CON HUMANOS (15k replays)")
    print("=" * 60)

    HUMAN_LOGS = Path("C:/vgc-projects/battle_logs/logs_gen9championsvgc2026regmc.json")
    if HUMAN_LOGS.exists():
        import re
        human_actions = []
        with HUMAN_LOGS.open(encoding="utf-8") as f:
            logs = json.load(f)
        for i, (_, (_, log)) in enumerate(logs.items()):
            if i > 3000:
                break
            for line in log.split("\n"):
                if line.startswith("|move|p1"):
                    parts = line.split("|")
                    if len(parts) > 3:
                        move_name = parts[3].strip().lower().replace(" ", "").replace("-", "").replace("'", "")
                        idx = move_vocab.get(move_name, -1)
                        if idx >= 0:
                            human_actions.append(idx)

        human_counter = Counter(human_actions)
        print(f"Total acciones humanas (muestra): {len(human_actions)}")

        # Comparar top 10 de ambos
        print("\n  Move         | Humano %  | Modelo %  | Ratio")
        print("  " + "-" * 55)
        for idx, count in action_counter.most_common(15):
            move_name = idx_to_move.get(idx, f"??? ({idx})")
            h_pct = human_counter.get(idx, 0) / max(1, len(human_actions)) * 100
            m_pct = count / len(actions) * 100
            ratio = m_pct / max(0.01, h_pct)
            marker = "🚨" if ratio > 3 else ""
            print(f"  {move_name:<12} | {h_pct:>7.2f}  | {m_pct:>7.2f}  | {ratio:>5.2f} {marker}")


if __name__ == "__main__":
    main()