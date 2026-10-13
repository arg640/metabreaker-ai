# src/rebuild_elites.py
"""
Reconstruye ga_elites.json desde ga_result.json del último run.
Útil cuando el GA crashea después de guardar el resultado pero antes
de actualizar los elites.

Uso:
    python -m src.rebuild_elites
"""
import json

from src.config import ELITES_FILE, GA_RESULT_FILE
from src.pokemon_pool import construir_pool


def main():
    POOL = construir_pool()
    name_to_idx = {p["pokemon"]: i for i, p in enumerate(POOL)}

    if not GA_RESULT_FILE.exists():
        print(f"[ERROR] No existe {GA_RESULT_FILE}")
        return

    with open(GA_RESULT_FILE, encoding="utf-8") as f:
        resultado = json.load(f)

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
                print(f"[WARN]  No encontrado en pool actual: {p['pokemon']}")
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
        print("[ERROR] No se pudo reconstruir ningún elite (nombres no coinciden con el pool)")
        return

    ELITES_FILE.parent.mkdir(parents=True, exist_ok=True)
    ELITES_FILE.write_text(
        json.dumps(elites, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"[OK] Guardados {len(elites)} elites en {ELITES_FILE}")
    for e in elites:
        print(f"   fitness={e['fitness']:.3f} | {', '.join(e['nombres'])}")


if __name__ == "__main__":
    main()