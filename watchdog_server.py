"""Watchdog: reinicia el servidor si deja de responder."""
import subprocess
import time
import requests
from pathlib import Path

SHOWDOWN_DIR = Path("C:/Users/ALVARO/Documents/metabreaker-ai/pokemon-showdown")
CHECK_INTERVAL = 60  # segundos
MAX_FAILS = 3


def servidor_vivo() -> bool:
    try:
        r = requests.get("http://localhost:8000", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def reiniciar_servidor():
    print("[WATCHDOG] Reiniciando servidor...")
    subprocess.run(["taskkill", "/F", "/IM", "node.exe"], capture_output=True)
    time.sleep(3)
    subprocess.Popen(
        ["node", "pokemon-showdown", "start", "--no-security"],
        cwd=SHOWDOWN_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    time.sleep(10)


def main():
    fails = 0
    while True:
        time.sleep(CHECK_INTERVAL)
        if servidor_vivo():
            fails = 0
            print("[WATCHDOG] Servidor OK")
        else:
            fails += 1
            print(f"[WATCHDOG] Servidor no responde ({fails}/{MAX_FAILS})")
            if fails >= MAX_FAILS:
                reiniciar_servidor()
                fails = 0


if __name__ == "__main__":
    main()