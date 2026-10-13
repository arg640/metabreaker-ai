# src/dagger_check.py
"""
Diagnóstico: ¿los datos DAgger están alineados con el modelo actual?

- Acc > 0.65  -> el modelo ya predice bien el DAgger (poco valor nuevo).
- Acc < 0.40  -> DAgger contradice al modelo (podría ser dañino).
- 0.40–0.65   -> útil para fine-tuning suave.
"""
import json

import numpy as np
import torch
import torch.nn as nn

from src.config import MODEL_PATH, N_ACTIONS, N_FEATURES, WINNER_LOGS


def main():
    if not WINNER_LOGS.exists():
        print(f"[WARN]  No existe {WINNER_LOGS}. Nada que analizar.")
        return

    ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    model = nn.Sequential(
        nn.Linear(N_FEATURES, 512), nn.ReLU(), nn.Dropout(0.3),
        nn.Linear(512, 256), nn.ReLU(), nn.Dropout(0.3),
        nn.Linear(256, N_ACTIONS),
    )
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    states, actions = [], []
    with WINNER_LOGS.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            states.append(d["f"])
            actions.append(d["a"])

    print(f"Total DAgger: {len(states)} pares")

    if not states:
        return

    X = torch.tensor(np.array(states), dtype=torch.float32)
    y = torch.tensor(actions, dtype=torch.long)

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

    acc = correct / max(1, total)
    print(f"\nAccuracy del modelo sobre DAgger: {acc:.3f}")
    print(f"Val_acc sobre datos humanos:      {ckpt.get('val_acc', '?')}")

    if acc > 0.65:
        print("\n[WARN]  El modelo ya predice bien el DAgger -> poco valor nuevo.")
    elif acc < 0.40:
        print("\n[FAIL] El DAgger contradice al modelo -> entrenar podría ser dañino.")
    else:
        print("\n[OK] DAgger alineado -> útil para fine-tuning suave.")


if __name__ == "__main__":
    main()