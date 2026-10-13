# src/dagger_retrain.py
"""
DAgger: fine-tuning del modelo BC existente con logs capturados por el GA
+ datos humanos originales (para evitar catastrophic forgetting).

Uso:
    python -m src.dagger_retrain
    python -m src.dagger_retrain --model models_bc/bc_model_2.pt
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
    MODEL_PATH,
    N_ACTIONS,
    N_FEATURES,
    WINNER_LOGS,
)
from src.log_parser import parse_log


EPOCHS = 50
PATIENCE = 10
VAL_SPLIT = 0.15
DAGGER_WEIGHT = 3.0  # Peso extra para datos DAgger


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, default=MODEL_PATH,
                   help="Checkpoint a hacer fine-tuning (in-place).")
    p.add_argument("--logs", type=Path, default=HUMAN_LOGS_PATH)
    p.add_argument("--dagger", type=Path, default=WINNER_LOGS)
    p.add_argument("--epochs", type=int, default=EPOCHS)
    p.add_argument("--patience", type=int, default=PATIENCE)
    p.add_argument("--dagger-weight", type=float, default=DAGGER_WEIGHT)
    return p.parse_args()


def evaluar(model, loader, criterion, device):
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


def cargar_datos_humanos(species_vocab, move_vocab, logs_path: Path):
    print(f"[LOAD] Cargando replays humanos desde {logs_path}...")
    with open(logs_path, encoding="utf-8") as f:
        logs = json.load(f)

    states, actions = [], []
    for i, (_, (_, log)) in enumerate(logs.items()):
        if i % 3000 == 0:
            print(f"  {i}/{len(logs)}")
        for feats, action in parse_log(log, species_vocab, move_vocab):
            states.append(feats)
            actions.append(action)

    print(f"  [OK] {len(states)} pares humanos")
    return states, actions


def cargar_datos_dagger(dagger_path: Path):
    if not dagger_path.exists():
        print(f"[WARN]  No existe {dagger_path}. Sin datos DAgger.")
        return [], []

    states, actions = [], []
    with dagger_path.open(encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
                states.append(np.array(d["f"], dtype=np.float32))
                actions.append(int(d["a"]))
            except Exception:
                continue

    print(f"  [OK] {len(states)} pares DAgger")
    return states, actions


def main():
    args = parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[DEVICE]  Device: {device}")

    print("\n[READ] Cargando vocabularios del modelo actual...")
    if not args.model.exists():
        raise FileNotFoundError(f"No existe {args.model}")
    ckpt_prev = torch.load(args.model, map_location="cpu", weights_only=False)
    species_vocab = ckpt_prev["species_vocab"]
    move_vocab = ckpt_prev["move_vocab"]
    print(f"  Species vocab: {len(species_vocab)}")
    print(f"  Move vocab:    {len(move_vocab)}")

    print("\n[STATS] Cargando datos...")
    h_states, h_actions = cargar_datos_humanos(species_vocab, move_vocab, args.logs)
    d_states, d_actions = cargar_datos_dagger(args.dagger)

    if not d_states:
        print("\n[ERROR] Sin datos DAgger. Abortando.")
        return

    print("\n[SHUFFLE] Combinando datasets...")
    print(f"  Humanos: {len(h_states)}")
    print(f"  DAgger:  {len(d_states)} (peso {args.dagger_weight}x)")

    n_rep = max(1, int(args.dagger_weight))
    all_states = h_states + (d_states * n_rep)
    all_actions = h_actions + (d_actions * n_rep)

    X = torch.tensor(np.array(all_states), dtype=torch.float32)
    y = torch.tensor(all_actions, dtype=torch.long)
    print(f"  Total: {len(X)} pares")

    n_total = len(X)
    n_val = int(n_total * VAL_SPLIT)
    perm = torch.randperm(n_total)
    val_idx = perm[:n_val]
    train_idx = perm[n_val:]

    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    print(f"  Train: {len(X_train)} | Val: {len(X_val)}")

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

    print("\n[LOOP] Cargando pesos previos (fine-tuning)...")
    model.load_state_dict(ckpt_prev["state_dict"])
    print(f"  Modelo previo: val_acc={ckpt_prev.get('val_acc', '?')}")

    optimizer = torch.optim.Adam(model.parameters(), lr=5e-4)
    criterion = nn.CrossEntropyLoss()

    best_val_loss = float("inf")
    best_epoch = 0
    epochs_sin_mejora = 0

    print(f"\n[START] Entrenando (max {args.epochs} epochs, paciencia {args.patience})...\n")

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
        val_loss, val_acc = evaluar(model, val_loader, criterion, device)

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
                },
                args.model,
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

    print(f"\n[OK] Mejor modelo: epoch {best_epoch} (val_loss={best_val_loss:.4f})")
    print(f"[FILE] Sobrescrito: {args.model}")
    print(f"[TIP] Val_acc previo: {ckpt_prev.get('val_acc', '?')}")
    print(f"[TIP] Val_acc nuevo:  {val_acc:.4f}")


if __name__ == "__main__":
    main()