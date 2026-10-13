# scripts/clean_emojis.py
"""
Reemplaza emojis y caracteres no-ASCII problemáticos por equivalentes ASCII
en todo src/ y scripts/. Deja acentos (á, é, í, ó, ú, ñ) intactos.

Uso:
    python -m scripts.clean_emojis
    python -m scripts.clean_emojis --dry-run    # solo muestra qué cambiaría
"""
import argparse
import re
from pathlib import Path


REEMPLAZOS = {
    "[LOAD]": "[LOAD]",
    "[FILE]": "[FILE]",
    "[READ]": "[READ]",
    "[STATS]": "[STATS]",
    "[IN]": "[IN]",
    "[OUT]": "[OUT]",
    "[OK]": "[OK]",
    "[WARN]": "[WARN]",
    "[WARN]": "[WARN]",
    "[ERROR]": "[ERROR]",
    "[FAIL]": "[FAIL]",
    "[CLOSED]": "[CLOSED]",
    "[SEED]": "[SEED]",
    "[DEVICE]": "[DEVICE]",
    "[DEVICE]": "[DEVICE]",
    "[TOP]": "[TOP]",
    "[START]": "[START]",
    "[STOP]": "[STOP]",
    "[FIRE]": "[FIRE]",
    "[TIP]": "[TIP]",
    "[SAVE]": "[SAVE]",
    "[BUILD]": "[BUILD]",
    "[SEARCH]": "[SEARCH]",
    "[LOOP]": "[LOOP]",
    "[SHUFFLE]": "[SHUFFLE]",
    "[TREE]": "[TREE]",
    "*": "*",
    "->": "->",
    "<-": "<-",
    "x": "x",
    "-": "-",
    "...": "...",
    "-": "-",
    "|": "|",
    "+": "+",
    "+": "+",
}


def _limpiar(texto: str) -> str:
    for emoji, repl in REEMPLAZOS.items():
        texto = texto.replace(emoji, repl)
    # Cualquier emoji que se haya escapado (rango BMP supplementary)
    texto = re.sub(r"[\U0001F000-\U0001FFFF]", "", texto)
    return texto


def _procesar_archivo(path: Path, dry_run: bool) -> bool:
    original = path.read_text(encoding="utf-8")
    nuevo = _limpiar(original)
    if nuevo == original:
        return False
    if not dry_run:
        path.write_text(nuevo, encoding="utf-8")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true",
                   help="No escribe, solo reporta.")
    args = p.parse_args()

    raices = [Path("src"), Path("scripts"), Path("tests")]
    cambiados = []

    for raiz in raices:
        if not raiz.exists():
            continue
        for py in raiz.rglob("*.py"):
            if "__pycache__" in str(py):
                continue
            if _procesar_archivo(py, args.dry_run):
                cambiados.append(py)

    if not cambiados:
        print("[OK] Sin cambios. Todo limpio.")
        return

    verbo = "cambiarían" if args.dry_run else "limpiados"
    print(f"[OK] {len(cambiados)} archivos {verbo}:")
    for f in cambiados:
        print(f"  - {f}")


if __name__ == "__main__":
    main()