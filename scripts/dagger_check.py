"""Diagnóstico: ¿los datos DAgger están alineados con el modelo actual?"""
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

DAGGER_PATH = Path("data/ga_logs/winner_logs.jsonl")
MODEL_PATH = Path("models_bc/bc_model.pt")

N_FEATURES = 28 + (100 * 4) + 150 + 4
N_ACTIONS = 150


def main():
    # Cargar modelo
    ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    model = nn.Sequential(
        nn.Linear(N_FEATURES, 512), nn.ReLU(), nn.Dropout(0.3),
        nn.Linear(512, 256), nn.ReLU(), nn.Dropout(0.3),
        nn.Linear(256, N_ACTIONS),
    )
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    # Cargar DAgger
    states = []
    actions = []
    with DAGGER_PATH.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            states.append(d["f"])
            actions.append(d["a"])

    print(f"Total DAgger: {len(states)} pares")
    X = torch.tensor(np.array(states), dtype=torch.float32)
    y = torch.tensor(actions, dtype=torch.long)

    # Evaluar con lotes
    correct = 0
    total = 0
    batch_size = 512
    with torch.no_grad():
        for i in range(0, len(X), batch_size):
            bx = X[i:i + batch_size]
            by = y[i:i + batch_size]
            preds = model(bx).argmax(1)
            correct += (preds == by).sum().item()
            total += len(by)

    acc = correct / total
    print(f"\nAccuracy del modelo sobre DAgger: {acc:.3f}")
    print(f"Val_acc sobre datos humanos:  {ckpt.get('val_acc'):.3f}")

    if acc > 0.65:
        print("\n⚠️ El modelo ya predice bien el DAgger → poco valor nuevo.")
    elif acc < 0.40:
        print("\n🔴 El DAgger contradice al modelo → entrenarlo podría ser dañino.")
    else:
        print("\n✅ El DAgger está alineado → útil para fine-tuning suave.")


if __name__ == "__main__":
    main()