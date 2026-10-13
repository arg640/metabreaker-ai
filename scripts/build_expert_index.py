# src/build_expert_index.py
"""
Construye el índice KDTree de estados humanos con sus acciones.

Este índice lo usa NeuralPlayer (expert lookup) para saber si un estado
del bot es "similar" a uno que un humano ya vio. Si lo es, se loggea como
par DAgger.

Uso:
    python -m src.build_expert_index
"""
import json
import pickle

import numpy as np
import torch
from sklearn.neighbors import KDTree

from src.config import (
    EXPERT_INDEX_PATH,
    HUMAN_LOGS_PATH,
    MODEL_PATH,
)
from src.log_parser import extract_compact, parse_log


def main():
    print("[READ] Cargando vocabularios del modelo...")
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"No existe {MODEL_PATH}. Entrená primero: python -m src.bc_train"
        )
    ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    species_vocab = ckpt["species_vocab"]
    move_vocab = ckpt["move_vocab"]
    print(f"  Species: {len(species_vocab)} | Moves: {len(move_vocab)}")

    print(f"\n[LOAD] Cargando replays humanos desde {HUMAN_LOGS_PATH}...")
    if not HUMAN_LOGS_PATH.exists():
        raise FileNotFoundError(f"No existe {HUMAN_LOGS_PATH}")
    with open(HUMAN_LOGS_PATH, encoding="utf-8") as f:
        logs = json.load(f)
    print(f"  {len(logs)} replays cargados")

    print("\n[BUILD] Extrayendo pares (estado_compacto, acción)...")
    all_compact = []
    all_actions = []
    for i, (_, (_, log)) in enumerate(logs.items()):
        if i % 2000 == 0:
            print(f"  {i}/{len(logs)}")
        for feats_full, action in parse_log(log, species_vocab, move_vocab):
            all_compact.append(extract_compact(feats_full))
            all_actions.append(action)

    print(f"\n  [OK] Total pares: {len(all_compact)}")

    X = np.array(all_compact, dtype=np.float32)
    y = np.array(all_actions, dtype=np.int32)
    print(f"  Shape X: {X.shape} | Shape y: {y.shape}")

    print("\n[TREE] Construyendo KDTree...")
    tree = KDTree(X, leaf_size=40)
    print("  [OK] KDTree construido")

    print(f"\n[SAVE] Guardando índice en {EXPERT_INDEX_PATH}...")
    EXPERT_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EXPERT_INDEX_PATH.open("wb") as f:
        pickle.dump(
            {
                "tree": tree,
                "X": X,
                "y": y,
                "n_samples": len(X),
            },
            f,
        )
    print("  [OK] Guardado")

    # Test rápido
    print("\n[SEARCH] Test de consulta:")
    test_state = X[0]
    dist, idx = tree.query(test_state.reshape(1, -1), k=3)
    print(f"  Estado de prueba (primeros 5 dims): {test_state[:5]}")
    print(f"  Vecinos: dist={dist[0]}, idx={idx[0]}")
    print(f"  Acciones: {y[idx[0]]}")


if __name__ == "__main__":
    main()