# scripts/plot_ga_progress.py
"""
Genera gráficas del progreso y resultados del GA.

Uso:
    python -m scripts.plot_ga_progress
    python -m scripts.plot_ga_progress --out data/processed/plots

Genera 4 PNGs:
    1. fitness_by_generation.png   -> fitness avg/max por generación
    2. top5_composition.png        -> qué Pokémon aparecen en el Top 5
    3. weakness_heatmap.png        -> debilidades del equipo ganador
    4. moves_histogram.png         -> moves elegidos por el modelo BC (si hay logs)
"""
import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend sin GUI
import matplotlib.pyplot as plt
import numpy as np

from src.config import (
    GA_RESULT_FILE,
    MODEL_PATH,
    PROCESSED_DIR,
    WINNER_LOGS,
)
from src.type_chart import TYPES, multiplicador


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=PROCESSED_DIR / "plots")
    return p.parse_args()


# ============================================================
# 1. FITNESS POR GENERACIÓN
# ============================================================
def plot_fitness(logbook, out_path):
    if not logbook:
        print("[WARN]  No hay logbook en ga_result.json. Saltando plot 1.")
        return

    gens = sorted(set(r["gen"] for r in logbook))
    avg_per_gen, max_per_gen = [], []
    for g in gens:
        filas = [r for r in logbook if r["gen"] == g]
        avg_per_gen.append(float(np.mean([r["avg"] for r in filas])))
        max_per_gen.append(float(np.max([r["max"] for r in filas])))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(gens, avg_per_gen, marker="o", linewidth=2, label="Avg por generación")
    ax.plot(gens, max_per_gen, marker="s", linewidth=2, label="Max por generación")
    ax.set_xlabel("Generación")
    ax.set_ylabel("Fitness")
    ax.set_title("Evolución del fitness durante el GA")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"  [OK] {out_path.name}")


# ============================================================
# 2. COMPOSICIÓN DEL TOP 5
# ============================================================
def plot_top5_composition(top5, out_path):
    if not top5:
        print("[WARN]  No hay top5 en ga_result.json. Saltando plot 2.")
        return

    conteo = Counter()
    for entry in top5:
        for p in entry["equipo"]:
            conteo[p["pokemon"]] += 1

    if not conteo:
        print("[WARN]  Top 5 vacío. Saltando plot 2.")
        return

    top = conteo.most_common(20)
    nombres = [n for n, _ in top]
    valores = [v for _, v in top]

    fig, ax = plt.subplots(figsize=(10, max(5, len(nombres) * 0.35)))
    y_pos = np.arange(len(nombres))
    ax.barh(y_pos, valores, color="#4C72B0")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(nombres)
    ax.invert_yaxis()
    ax.set_xlabel("Apariciones en el Top 5")
    ax.set_title("Pokémon más frecuentes en el Top 5 del GA")
    for i, v in enumerate(valores):
        ax.text(v + 0.05, i, str(v), va="center")
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"  [OK] {out_path.name}")


# ============================================================
# 3. HEATMAP DE DEBILIDADES DEL EQUIPO GANADOR
# ============================================================
def plot_weakness_heatmap(equipo, out_path):
    if not equipo or len(equipo) == 0:
        print("[WARN]  No hay equipo ganador. Saltando plot 3.")
        return

    # matriz: filas = Pokémon, columnas = tipo atacante
    matriz = np.zeros((len(equipo), len(TYPES)))
    for i, p in enumerate(equipo):
        for j, atk in enumerate(TYPES):
            matriz[i, j] = multiplicador(atk, p["types"])

    fig, ax = plt.subplots(figsize=(14, max(4, len(equipo) * 0.6)))
    im = ax.imshow(matriz, cmap="RdYlGn_r", vmin=0, vmax=4, aspect="auto")

    ax.set_xticks(np.arange(len(TYPES)))
    ax.set_xticklabels(TYPES, rotation=45, ha="right")
    ax.set_yticks(np.arange(len(equipo)))
    ax.set_yticklabels([p["pokemon"] for p in equipo])

    # anotar valores
    for i in range(len(equipo)):
        for j in range(len(TYPES)):
            v = matriz[i, j]
            if v != 1.0:  # solo anotar lo relevante
                txt = f"{v:.1f}".rstrip("0").rstrip(".")
                color = "white" if v >= 2 else "black"
                ax.text(j, i, txt, ha="center", va="center",
                        color=color, fontsize=8)

    ax.set_title("Debilidades defensivas del equipo ganador\n"
                 "(rojo = débil, verde = resistente, blanco = neutral)")
    fig.colorbar(im, ax=ax, label="Multiplicador de daño")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"  [OK] {out_path.name}")


# ============================================================
# 4. HISTOGRAMA DE MOVES ELEGIDOS POR EL MODELO BC
# ============================================================
def plot_moves_histogram(out_path):
    if not WINNER_LOGS.exists():
        print(f"[WARN]  No existe {WINNER_LOGS}. Saltando plot 4.")
        return

    import torch
    if not MODEL_PATH.exists():
        print(f"[WARN]  No existe {MODEL_PATH}. Saltando plot 4.")
        return

    ckpt = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
    idx_to_move = {v: k for k, v in ckpt["move_vocab"].items()}

    acciones = []
    with WINNER_LOGS.open(encoding="utf-8") as f:
        for line in f:
            try:
                acciones.append(json.loads(line)["a"])
            except Exception:
                continue

    if not acciones:
        print("[WARN]  winner_logs vacío. Saltando plot 4.")
        return

    conteo = Counter(acciones)
    top = conteo.most_common(20)
    nombres = [idx_to_move.get(i, f"??? ({i})") for i, _ in top]
    valores = [c for _, c in top]

    fig, ax = plt.subplots(figsize=(10, 6))
    y_pos = np.arange(len(nombres))
    ax.barh(y_pos, valores, color="#55A868")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(nombres)
    ax.invert_yaxis()
    ax.set_xlabel("Frecuencia")
    ax.set_title("Top 20 movimientos elegidos por el modelo BC en batallas ganadoras")
    for i, v in enumerate(valores):
        ax.text(v + 0.5, i, str(v), va="center")
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"  [OK] {out_path.name}")


# ============================================================
# MAIN
# ============================================================
def main():
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if not GA_RESULT_FILE.exists():
        print(f"[ERROR] No existe {GA_RESULT_FILE}. Corré primero el GA.")
        return

    with GA_RESULT_FILE.open(encoding="utf-8") as f:
        resultado = json.load(f)

    print(f"[STATS] Generando plots en {args.out}/\n")

    plot_fitness(resultado.get("logbook", []),
                 args.out / "fitness_by_generation.png")

    top5 = resultado.get("top5", [])
    plot_top5_composition(top5, args.out / "top5_composition.png")

    equipo_ganador = resultado.get("equipo") or (top5[0]["equipo"] if top5 else [])
    plot_weakness_heatmap(equipo_ganador, args.out / "weakness_heatmap.png")

    plot_moves_histogram(args.out / "moves_histogram.png")

    print(f"\n[OK] Listo. Abrí las imágenes en: {args.out.resolve()}")


if __name__ == "__main__":
    main()