# src/export_team.py
"""
Exporta los 5 mejores equipos de ga_result.json al formato Showdown.
"""
import json
from pathlib import Path

from src.pokemon_set import PokemonSet


def exportar_equipo_a_showdown(equipo: list[dict]) -> str:
    sets = [PokemonSet.from_dict(p) for p in equipo]
    return "\n\n".join(s.to_showdown() for s in sets)


def main():
    ruta_json = Path("data/processed/ga_result.json")
    if not ruta_json.exists():
        print(f"❌ No existe {ruta_json}. Corre primero el GA.")
        return

    with open(ruta_json, encoding="utf-8") as f:
        resultado = json.load(f)

    top5 = resultado.get(
        "top5",
        [{"rank": 1, "equipo": resultado["equipo"], "fitness": resultado["fitness"]}],
    )

    out_dir = Path("data/processed")
    for entrada in top5:
        rank = entrada["rank"]
        equipo = entrada["equipo"]
        texto = exportar_equipo_a_showdown(equipo)

        ruta_export = out_dir / f"equipo_final_{rank}.txt"
        ruta_export.write_text(texto, encoding="utf-8")

        print(f"\n{'=' * 60}")
        print(f"🏆 EQUIPO #{rank} (fitness {entrada['fitness']:.3f})")
        print(f"{'=' * 60}")
        for p in equipo:
            print(f"  - {p['pokemon']}")
        print(f"\n  Guardado en: {ruta_export}")

    print(f"\n💡 Cada archivo se puede importar en el Team Builder de Showdown.")


if __name__ == "__main__":
    main()