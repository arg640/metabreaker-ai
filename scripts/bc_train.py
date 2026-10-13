# src/bc_train.py
"""
Behavior Cloning v8 — features ricas SIN leakage de moves.

Uso:
    python -m src.bc_train --seed 47  --output models_bc/bc_model.pt
    python -m src.bc_train --seed 123 --output models_bc/bc_model_2.pt

El segundo modelo sirve para eliminar el sesgo de self-play en el GA:
en vez de que el mismo agente se enfrente a sí mismo, se enfrentan dos
agentes independientes entrenados con seeds distintos.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from src.config import (
    HUMAN_LOGS_PATH,
    MODELS_DIR,
    N_ACTIONS,
    N_FEATURES,
)
from src.log_parser import build_vocabs, parse_log


EPOCHS = 200
PATIENCE = 20
VAL_SPLIT = 0.15


def parse_args():
    p = argparse.ArgumentParser(description="Entrena un modelo BC.")
    p.add_argument("--seed", type=int, default=47,
                   help="Semilla (distinta -> modelo distinto -> sin self-play).")
    p.add_argument("--output", type=Path, default=MODELS_DIR / "bc_model.pt",
                   help="Ruta donde guardar el checkpoint.")
    p.add_argument("--logs", type=Path, default=HUMAN_LOGS_PATH,
                   help="Archivo .json con los replays humanos.")
    p.add_argument("--epochs", type=int, default=EPOCHS)
    p.add_argument("--patience", type=int, default=PATIENCE)
    return p.parse_args()


def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    with torch.no_grad():
        for bx, by in loader:
            bx, by = bx.to(device), by.to(device)
            logits = model(bx)
            loss = criterion(logits, by)
            total_loss += loss.item()
            correct += (logits.argmax(1) == by).sum().item()
            total += len(by)
    return total_loss / max(1, len(loader)), correct / max(1, total)


def main():
    args = parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    # ------- Dispositivo -------
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[DEVICE]  Device: {device}")
    print(f"[SEED] Seed: {args.seed}")
    print(f"[FILE] Output: {args.output}")
    print(f"[LOAD] Logs: {args.logs}\n")

    if not args.logs.exists():
        raise FileNotFoundError(f"No existe {args.logs}")

    with open(args.logs, encoding="utf-8") as f:
        logs = json.load(f)

    print(f"[READ] Construyendo vocabularios con {len(logs)} replays...")
    species_vocab, move_vocab = build_vocabs(logs)
    print(f"   Species vocab: {len(species_vocab)}")
    print(f"   Move vocab:    {len(move_vocab)}\n")

    print("[BUILD] Extrayendo pares (features, acción)...")
    all_states: list[np.ndarray] = []
    all_actions: list[int] = []
    for i, (_, (_, log)) in enumerate(logs.items()):
        if i % 1000 == 0:
            print(f"   {i}/{len(logs)}")
        for feats, action in parse_log(log, species_vocab, move_vocab):
            all_states.append(feats)
            all_actions.append(action)

    print(f"\n  [OK] Total pares: {len(all_states)}")
    print(f"  [OK] Features: {N_FEATURES}\n")

    if len(all_states) < 1000:
        print("[WARN]  Muy pocos datos. Abortando.")
        return

    X = torch.tensor(np.array(all_states), dtype=torch.float32)
    y = torch.tensor(all_actions, dtype=torch.long)

    n_total = len(X)
    n_val = int(n_total * VAL_SPLIT)
    perm = torch.randperm(n_total)
    val_idx = perm[:n_val]
    train_idx = perm[n_val:]

    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]

    print(f"  Train: {len(X_train)} | Val: {len(X_val)}\n")

    train_loader = DataLoader(
        TensorDataset(X_train, y_train), batch_size=256, shuffle=True
    )
    val_loader = DataLoader(
        TensorDataset(X_val, y_val), batch_size=512, shuffle=False
    )

    model = nn.Sequential(
        nn.Linear(N_FEATURES, 512),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(512, 256),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(256, N_ACTIONS),
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()

    best_val_loss = float("inf")
    best_epoch = 0
    epochs_sin_mejora = 0

    args.output.parent.mkdir(parents=True, exist_ok=True)

    print(f"[START] Entrenando (max {args.epochs} epochs, paciencia {args.patience})...\n")

    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            logits = model(bx)
            loss = criterion(logits, by)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            correct += (logits.argmax(1) == by).sum().item()
            total += len(by)

        train_acc = correct / max(1, total)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)

        marker = ""
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch + 1
            epochs_sin_mejora = 0
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "species_vocab": species_vocab,
                    "move_vocab": move_vocab,
                    "n_features": N_FEATURES,
                    "n_actions": N_ACTIONS,
                    "best_epoch": best_epoch,
                    "best_val_loss": best_val_loss,
                    "val_acc": val_acc,
                    "seed": args.seed,
                },
                args.output,
            )
            marker = " *"
        else:
            epochs_sin_mejora += 1

        print(
            f"Epoch {epoch+1:3}/{args.epochs} | "
            f"train_acc={train_acc:.3f} | "
            f"val_acc={val_acc:.3f} val_loss={val_loss:.4f}{marker}"
        )

        if epochs_sin_mejora >= args.patience:
            print("\n[STOP] Early stopping.")
            break

    print(f"\n[OK] Mejor epoch: {best_epoch} (val_loss={best_val_loss:.4f})")
    print(f"[FILE] Guardado en: {args.output}")


if __name__ == "__main__":
    main()