# src/scraper_pikalytics.py
import requests
from pathlib import Path

URL = "https://www.pikalytics.com/pokedex"
OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def descargar_html(url: str, nombre_archivo: str) -> None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    print(f"⬇️ Descargando {url}...")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    ruta = OUTPUT_DIR / nombre_archivo
    ruta.write_text(response.text, encoding="utf-8")
    print(f"✅ Guardado: {ruta} ({len(response.text)} caracteres)")

    if "Rillaboom" in response.text:
        print("🎯 ¡'Rillaboom' encontrado en el HTML! Los datos están ahí.")
    else:
        print("⚠️ 'Rillaboom' NO está en el HTML. Necesitaremos otra estrategia.")

if __name__ == "__main__":
    descargar_html(URL, "pikalytics_regmc.html")