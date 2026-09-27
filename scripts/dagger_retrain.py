"""DAgger: fine-tuning del modelo BC con logs del GA + datos originales."""
import json
import re
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# Paths
LOGS_PATH = Path("C:/vgc-projects/battle_logs/logs_gen9championsvgc2026regmc.json")
DAGGER_PATH = Path("data/ga_logs/winner_logs.jsonl")
OUTPUT_DIR = Path("models_bc")
OUTPUT_DIR.mkdir(exist_ok=True)

# Configuración idéntica a bc_train.py v7
MAX_SPECIES = 100
MAX_ACTIONS = 150
N_FIXED = 28
N_SPECIES_BLOCK = MAX_SPECIES * 4
N_MOVES_BLOCK = MAX_ACTIONS
N_COUNT_BLOCK = 4
N_FEATURES = N_FIXED + N_SPECIES_BLOCK + N_MOVES_BLOCK + N_COUNT_BLOCK
N_ACTIONS = MAX_ACTIONS

EPOCHS = 50
PATIENCE = 10
VAL_SPLIT = 0.15
DAGGER_WEIGHT = 3.0  # Peso extra para los datos DAgger (on-policy)


def norm(name):
    return name.lower().replace(" ", "").replace("-", "").replace("'", "")


def cargar_vocab_del_modelo():
    """Carga el vocabulario del modelo actual para mantener consistencia."""
    ckpt = torch.load(OUTPUT_DIR / "bc_model.pt", map_location="cpu", weights_only=False)
    return ckpt["species_vocab"], ckpt["move_vocab"], ckpt


def parse_log_humano(log, species_vocab, move_vocab):
    """Parsea un replay humano (idéntico a bc_train.py)."""
    pairs = []
    p1_active = [None, None]
    p2_active = [None, None]
    p1_hp = [0.0, 0.0]
    p2_hp = [0.0, 0.0]
    p1_status = [0, 0]
    p2_status = [0, 0]
    p1_fainted = [0, 0]
    p2_fainted = [0, 0]

    moves_seen = {"p1a": set(), "p1b": set(), "p2a": set(), "p2b": set()}
    tailwind_p1 = 0
    tailwind_p2 = 0
    trick_room = 0
    weather = [0, 0, 0, 0, 0]
    terrain = [0, 0, 0, 0, 0]
    turno = 0

    def species_one_hot(sp_name, buf, off):
        idx = species_vocab.get(sp_name, -1)
        if idx >= 0:
            buf[off + idx] = 1.0

    for line in log.split("\n"):
        parts = line.split("|")
        if len(parts) < 3:
            continue
        t = parts[1]

        if t == "turn":
            try:
                turno = int(parts[2])
            except ValueError:
                pass
        elif t in ("switch", "drag"):
            side = parts[2]
            if ": " in side:
                slot_str = side.split(":")[0]
                sp_name = norm(side.split(": ")[1].strip().split(",")[0])
                hp_match = re.search(r"(\d+)/(\d+)", parts[3]) if len(parts) > 3 else None
                hp_frac = (int(hp_match.group(1)) / max(1, int(hp_match.group(2)))) if hp_match else 1.0
                slot_idx = 0 if slot_str.endswith("a") else 1
                if slot_str in moves_seen:
                    moves_seen[slot_str] = set()
                if slot_str.startswith("p1"):
                    p1_active[slot_idx] = sp_name
                    p1_hp[slot_idx] = hp_frac
                    p1_status[slot_idx] = 0
                    p1_fainted[slot_idx] = 0
                else:
                    p2_active[slot_idx] = sp_name
                    p2_hp[slot_idx] = hp_frac
                    p2_status[slot_idx] = 0
                    p2_fainted[slot_idx] = 0
        elif t in ("-damage", "-heal"):
            side = parts[2]
            if ": " in side:
                slot_str = side.split(":")[0]
                hp_match = re.search(r"(\d+)/(\d+)", parts[3]) if len(parts) > 3 else None
                if hp_match:
                    hp_frac = int(hp_match.group(1)) / max(1, int(hp_match.group(2)))
                    slot_idx = 0 if slot_str.endswith("a") else 1
                    if slot_str.startswith("p1"):
                        p1_hp[slot_idx] = hp_frac
                    else:
                        p2_hp[slot_idx] = hp_frac
        elif t == "-status":
            side = parts[2]
            if ": " in side:
                slot_str = side.split(":")[0]
                slot_idx = 0 if slot_str.endswith("a") else 1
                if slot_str.startswith("p1"):
                    p1_status[slot_idx] = 1
                else:
                    p2_status[slot_idx] = 1
        elif t == "faint":
            side = parts[2]
            if ": " in side:
                slot_str = side.split(":")[0]
                slot_idx = 0 if slot_str.endswith("a") else 1
                if slot_str.startswith("p1"):
                    p1_hp[slot_idx] = 0.0
                    p1_fainted[slot_idx] = 1
                else:
                    p2_hp[slot_idx] = 0.0
                    p2_fainted[slot_idx] = 1
        elif t == "-sidestart" and "tailwind" in line.lower():
            tailwind_p1 = 1 if parts[2] == "p1" else 0
            tailwind_p2 = 1 if parts[2] == "p2" else tailwind_p2
        elif t == "-fieldstart" and "trickroom" in line.lower():
            trick_room = 1
        elif t == "-weather":
            w = line.lower()
            weather = [0, 0, 0, 0, 0]
            if "sunnyday" in w: weather[1] = 1
            elif "raindance" in w: weather[2] = 1
            elif "sandstorm" in w: weather[3] = 1
            elif "snow" in w or "hail" in w: weather[4] = 1
            else: weather[0] = 1
        elif t == "-fieldstart" and "terrain" in line.lower():
            f = line.lower()
            terrain = [0, 0, 0, 0, 0]
            if "electric" in f: terrain[1] = 1
            elif "grassy" in f: terrain[2] = 1
            elif "psychic" in f: terrain[3] = 1
            elif "misty" in f: terrain[4] = 1
            else: terrain[0] = 1
        elif t == "move":
            side = parts[2]
            if ": " in side:
                slot_str = side.split(":")[0]
                move_name = norm(parts[3].strip())
                if slot_str.startswith("p1"):
                    action_id = move_vocab.get(move_name, -1)
                    if action_id >= 0:
                        feats = np.zeros(N_FEATURES, dtype=np.float32)
                        feats[0] = turno / 20.0
                        feats[1:5] = [p1_hp[0], p1_hp[1], p2_hp[0], p2_hp[1]]
                        feats[5:9] = [p1_status[0], p1_status[1], p2_status[0], p2_status[1]]
                        feats[9:13] = [p1_fainted[0], p1_fainted[1], p2_fainted[0], p2_fainted[1]]
                        feats[13] = tailwind_p1
                        feats[14] = tailwind_p2
                        feats[15] = trick_room
                        feats[16:21] = weather
                        feats[21:26] = terrain
                        feats[26] = 0 if slot_str.endswith("a") else 1

                        species_one_hot(p1_active[0] or "", feats, N_FIXED)
                        species_one_hot(p1_active[1] or "", feats, N_FIXED + MAX_SPECIES)
                        species_one_hot(p2_active[0] or "", feats, N_FIXED + MAX_SPECIES * 2)
                        species_one_hot(p2_active[1] or "", feats, N_FIXED + MAX_SPECIES * 3)

                        moves_off = N_FIXED + N_SPECIES_BLOCK
                        for mv in moves_seen[slot_str]:
                            idx = move_vocab.get(mv, -1)
                            if idx >= 0:
                                feats[moves_off + idx] = 1.0

                        counts_off = moves_off + N_MOVES_BLOCK
                        feats[counts_off + 0] = min(len(moves_seen["p1a"]) / 4.0, 1.0)
                        feats[counts_off + 1] = min(len(moves_seen["p1b"]) / 4.0, 1.0)
                        feats[counts_off + 2] = min(len(moves_seen["p2a"]) / 4.0, 1.0)
                        feats[counts_off + 3] = min(len(moves_seen["p2b"]) / 4.0, 1.0)

                        pairs.append((feats, action_id))

                if slot_str in moves_seen:
                    moves_seen[slot_str].add(move_name)

    return pairs


def cargar_datos_humanos(species_vocab, move_vocab):
    """Carga los 15k replays humanos."""
    print(f"📂 Cargando replays humanos...")
    with open(LOGS_PATH, encoding="utf-8") as f:
        logs = json.load(f)

    states = []
    actions = []
    for i, (_, (_, log)) in enumerate(logs.items()):
        if i % 3000 == 0:
            print(f"  {i}/{len(logs)}")
        for feats, action in parse_log_humano(log, species_vocab, move_vocab):
            states.append(feats)
            actions.append(action)

    print(f"  ✅ {len(states)} pares humanos")
    return states, actions


def cargar_datos_dagger():
    """Carga los logs capturados por el GA."""
    if not DAGGER_PATH.exists():
        print(f"⚠️ No existe {DAGGER_PATH}. Sin datos DAgger.")
        return [], []

    states = []
    actions = []
    with DAGGER_PATH.open(encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
                states.append(np.array(d["f"], dtype=np.float32))
                actions.append(int(d["a"]))
            except Exception:
                continue

    print(f"  ✅ {len(states)} pares DAgger")
    return states, actions


def evaluar(model, loader, criterion):
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
    return total_loss / len(loader), correct / total


if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥️ Device: {device}")

    print("\n📖 Cargando vocabularios del modelo actual...")
    species_vocab, move_vocab, ckpt_prev = cargar_vocab_del_modelo()
    print(f"  Species vocab: {len(species_vocab)}")
    print(f"  Move vocab: {len(move_vocab)}")

    print("\n📊 Cargando datos...")
    h_states, h_actions = cargar_datos_humanos(species_vocab, move_vocab)
    d_states, d_actions = cargar_datos_dagger()

    if not d_states:
        print("\n❌ Sin datos DAgger. Abortando.")
        sys.exit(1)

    # Combinar con peso DAgger
    print(f"\n🔀 Combinando datasets...")
    print(f"  Humanos: {len(h_states)}")
    print(f"  DAgger: {len(d_states)} (peso {DAGGER_WEIGHT}x)")

    # Repetir DAgger N veces para darle más peso
    dagger_states_rep = d_states * int(DAGGER_WEIGHT)
    dagger_actions_rep = d_actions * int(DAGGER_WEIGHT)

    all_states = h_states + dagger_states_rep
    all_actions = h_actions + dagger_actions_rep

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

    train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=256, shuffle=True)
    val_loader = DataLoader(TensorDataset(X_val, y_val), batch_size=512, shuffle=False)

    # Modelo
    model = nn.Sequential(
        nn.Linear(N_FEATURES, 512),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(512, 256),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(256, N_ACTIONS),
    ).to(device)

    # Cargar pesos del modelo anterior (fine-tuning)
    print("\n🔁 Cargando pesos previos (fine-tuning)...")
    model.load_state_dict(ckpt_prev["state_dict"])
    print(f"  Modelo previo tenía val_acc={ckpt_prev.get('val_acc', '?')}")

    optimizer = torch.optim.Adam(model.parameters(), lr=5e-4)  # LR reducido para fine-tuning
    criterion = nn.CrossEntropyLoss()

    best_val_loss = float("inf")
    best_epoch = 0
    epochs_sin_mejora = 0

    print(f"\n🚀 Entrenando (max {EPOCHS} epochs, paciencia {PATIENCE})...\n")

    for epoch in range(EPOCHS):
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
        train_acc = correct / total

        val_loss, val_acc = evaluar(model, val_loader, criterion)

        marker = ""
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch + 1
            epochs_sin_mejora = 0
            torch.save({
                "state_dict": model.state_dict(),
                "species_vocab": species_vocab,
                "move_vocab": move_vocab,
                "n_features": N_FEATURES,
                "n_actions": N_ACTIONS,
                "best_epoch": best_epoch,
                "best_val_loss": best_val_loss,
                "val_acc": val_acc,
            }, OUTPUT_DIR / "bc_model.pt")
            marker = " ⭐"
        else:
            epochs_sin_mejora += 1

        print(f"Epoch {epoch+1:3}/{EPOCHS} | train_acc={train_acc:.3f} | val_acc={val_acc:.3f} val_loss={val_loss:.4f}{marker}")

        if epochs_sin_mejora >= PATIENCE:
            print(f"\n🛑 Early stopping.")
            break

    print(f"\n✅ Mejor modelo: epoch {best_epoch} (val_loss={best_val_loss:.4f})")
    print(f"📁 Guardado en: {OUTPUT_DIR / 'bc_model.pt'}")
    print(f"\n💡 Val_acc previo: {ckpt_prev.get('val_acc', '?')}")
    print(f"💡 Val_acc nuevo: {best_val_loss:.4f}")