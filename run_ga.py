# run_ga.py
import subprocess
import sys

with open("data/processed/ga_run.log", "w", encoding="utf-8") as f:
    p = subprocess.Popen(
        [sys.executable, "-m", "src.ga"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    for line in p.stdout:
        print(line, end="")
        f.write(line)
        f.flush()
    p.wait()