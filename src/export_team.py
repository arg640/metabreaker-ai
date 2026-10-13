# src/export_team.py
"""Exporta el Top 5 del GA a formato Showdown."""
import json

from src.config import GA_RESULT_FILE, PROCESSED_DIR
from src.pokemon_pool import limpiar_equipo
from src.pokemon_set import PokemonSet


def exportar_equipo_a_showdown(equipo: list[dict]) -> str:
    sets = [PokemonSet.from_dict(p) for p in equipo]
    return "\n\n".join(s.to_showdown() for s in sets)


def main():
    if not GA_RESULT_FILE.exists():
        print(f"[ERROR] No existe {GA_RESULT_FILE}. Corre primero el GA.")
        return

    with open(GA_RESULT_FILE, encoding="utf-8") as f:
        resultado = json.load(f)

    top5 = resultado.get(
        "top5",
        [{
            "rank": 1,
            "equipo": resultado["equipo"],
            "fitness": resultado["fitness"],
        }],
    )

    for entrada in top5:
        rank = entrada["rank"]
        equipo = limpiar_equipo(entrada["equipo"])
        texto = exportar_equipo_a_showdown(equipo)

        ruta_export = PROCESSED_DIR / f"equipo_final_{rank}.txt"
        ruta_export.write_text(texto, encoding="utf-8")

        print(f"\n{'=' * 60}")
        print(f"[TOP] EQUIPO #{rank} (fitness {entrada['fitness']:.3f})")
        print(f"{'=' * 60}")
        for p in equipo:
            item = p.get("item") or "(sin item)"
            print(f"  - {p['pokemon']:<25} @ {item}")
        print(f"\n  Guardado en: {ruta_export}")

    print("\n[TIP] Aplicado Item Clause, Mega Clause y limpieza de habilidades.")


if __name__ == "__main__":
    main()