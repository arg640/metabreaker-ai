# src/rebuild_elites.py
"""
Reconstruye ga_elites.json desde ga_result.json del último run.
Útil cuando el GA crashea después de guardar el resultado pero antes
de actualizar los elites.
"""
import json
from pathlib import Path

from src.pokemon_pool import construir_pool

POOL = construir_pool()
# Mapa nombre -> índice en el pool
name_to_idx = {p["pokemon"]: i for i, p in enumerate(POOL)}

RESULT_FILE = Path("data/processed/ga_result.json")
ELITES_FILE = Path("data/processed/ga_elites.json")


def main():
    if not RESULT_FILE.exists():
        print(f"❌ No existe {RESULT_FILE}")
        return

    with open(RESULT_FILE, encoding="utf-8") as f:
        resultado = json.load(f)

    # Coger top5 del resultado; si no hay, usar solo el equipo ganador
    top5 = resultado.get("top5", [])
    if not top5:
        top5 = [{
            "rank": 1,
            "equipo": resultado["equipo"],
            "fitness": resultado["fitness"],
        }]

    elites = []
    for entry in top5:
        equipo = entry["equipo"]
        genoma = []
        valido = True
        for p in equipo:
            idx = name_to_idx.get(p["pokemon"])
            if idx is None:
                print(f"⚠️  No encontrado en pool actual: {p['pokemon']}")
                valido = False
                break
            genoma.append(idx)

        if valido and len(genoma) == 6:
            elites.append({
                "genoma": genoma,
                "fitness": entry["fitness"],
                "nombres": [p["pokemon"] for p in equipo],
            })

    if not elites:
        print("❌ No se pudo reconstruir ningún elite (nombres no coinciden con el pool)")
        return

    ELITES_FILE.parent.mkdir(parents=True, exist_ok=True)
    ELITES_FILE.write_text(
        json.dumps(elites, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"✅ Guardados {len(elites)} elites en {ELITES_FILE}")
    for e in elites:
        print(f"   fitness={e['fitness']:.3f} | {', '.join(e['nombres'])}")


if __name__ == "__main__":
    main()