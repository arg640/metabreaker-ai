# src/inspect_html.py
from bs4 import BeautifulSoup
from collections import Counter

with open("data/raw/pikalytics_regmc.html", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# 1) Contexto alrededor de Rillaboom
print("=== 1. Contexto de Rillaboom ===")
rillaboom = soup.find(string="Rillaboom")
if rillaboom:
    print(rillaboom.parent.parent.prettify()[:3000])
else:
    print("No se encontro 'Rillaboom'")

# 2) Tablas presentes
print("\n=== 2. Tablas encontradas ===")
tablas = soup.find_all("table")
if not tablas:
    print("  (no hay tablas <table>)")
for i, tabla in enumerate(tablas):
    print(f"Tabla {i}: {len(tabla.find_all('tr'))} filas")

# 3) Clases CSS mas comunes
print("\n=== 3. Clases CSS mas comunes ===")
clases = Counter()
for tag in soup.find_all(class_=True):
    for c in tag.get("class", []):
        clases[c] += 1
for c, n in clases.most_common(25):
    print(f"  {c}: {n}")

# 4) Elementos con data-* attributes (a veces guardan info)
print("\n=== 4. Elementos con atributos data-* ===")
data_attrs = Counter()
for tag in soup.find_all(attrs=True):
    for attr in tag.attrs:
        if attr.startswith("data-"):
            data_attrs[attr] += 1
for a, n in data_attrs.most_common(15):
    print(f"  {a}: {n}")