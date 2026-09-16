# src/export_team.py
import json
from pathlib import Path

from src.pokemon_set import PokemonSet
from src.pokemon_pool import limpiar_equipo


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

        # ← CAMBIO CLAVE: aplicar limpiar_equipo (Item Clause + habilidades + species)
        equipo_limpio = limpiar_equipo(equipo)

        texto = exportar_equipo_a_showdown(equipo_limpio)

        ruta_export = out_dir / f"equipo_final_{rank}.txt"
        ruta_export.write_text(texto, encoding="utf-8")

        print(f"\n{'=' * 60}")
        print(f"🏆 EQUIPO #{rank} (fitness {entrada['fitness']:.3f})")
        print(f"{'=' * 60}")
        for p in equipo_limpio:
            item = p.get("item") or "(sin item)"
            print(f"  - {p['pokemon']:<25} @ {item}")
        print(f"\n  Guardado en: {ruta_export}")

    print(f"\n💡 Aplicado Item Clause y limpieza de habilidades.")


if __name__ == "__main__":
    main()