# src/ga.py
"""
Algoritmo Genético para evolucionar equipos anti-meta.
Usa DEAP para la evolución y src.simulator para evaluar el fitness.
"""
import json
import random
from pathlib import Path

from deap import base, creator, tools, algorithms

from src.pokemon_pool import construir_pool
from src.simulator import simular_enfrentamiento

# ============ CONFIGURACIÓN ============
EQUIPO_SIZE = 6
N_BATALLAS_POR_RIVAL = 2   # batallas por cada equipo meta
N_RIVALES = 5              # cuántos equipos meta usar como referencia
POP_SIZE = 10              # población inicial
N_GEN = 3                  # generaciones
CXPB = 0.5                 # probabilidad de cruce
MUTPB = 0.3                # probabilidad de mutación
SEED = 42

random.seed(SEED)


# ============ DATOS GLOBALES ============
POOL = construir_pool()
N_POOL = len(POOL)

with open("data/processed/sample_teams.json", encoding="utf-8") as f:
    EQUIPOS_META = json.load(f)

# Seleccionamos N_RIVALES equipos del meta como referencia
RIVALES = EQUIPOS_META[:N_RIVALES]


# ============ GENOMA Y FITNESS ============
# El genoma es una lista de EQUIPO_SIZE enteros (índices en el pool), sin repetir.
# El fitness es el winrate promedio contra los rivales.

creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)


def crear_individuo():
    """Crea un equipo aleatorio de 6 Pokémon del pool, sin repetir."""
    indices = random.sample(range(N_POOL), EQUIPO_SIZE)
    return creator.Individual(indices)


def evaluar(individuo):
    """Fitness: winrate promedio del equipo contra los rivales."""
    equipo = [POOL[i] for i in individuo]

    winrates = []
    for rival in RIVALES:
        wr = simular_enfrentamiento(equipo, rival, n_batallas=N_BATALLAS_POR_RIVAL)
        winrates.append(wr)

    fitness = sum(winrates) / len(winrates) if winrates else 0.0
    return (fitness,)


def cruzar(ind1, ind2):
    """Cruce: toma 3 genes de cada padre y rellena con aleatorios si hay duplicados."""
    hijo1, hijo2 = [], []

    for i in range(EQUIPO_SIZE):
        if i < EQUIPO_SIZE // 2:
            hijo1.append(ind1[i])
            hijo2.append(ind2[i])
        else:
            hijo1.append(ind2[i])
            hijo2.append(ind1[i])

    # Deduplicación: reemplaza duplicados por genes aleatorios no presentes
    hijo1 = _deduplicar(hijo1)
    hijo2 = _deduplicar(hijo2)

    ind1[:] = hijo1
    ind2[:] = hijo2
    return ind1, ind2


def _deduplicar(genes: list[int]) -> list[int]:
    """Asegura que no haya índices repetidos en la lista de genes."""
    vistos = set()
    resultado = []
    for g in genes:
        if g not in vistos:
            vistos.add(g)
            resultado.append(g)
    # Rellena si faltan genes
    while len(resultado) < EQUIPO_SIZE:
        nuevo = random.randrange(N_POOL)
        if nuevo not in vistos:
            vistos.add(nuevo)
            resultado.append(nuevo)
    return resultado


def mutar(individuo, indpb=0.3):
    """Mutación: reemplaza algunos genes por otros aleatorios del pool."""
    for i in range(len(individuo)):
        if random.random() < indpb:
            # Encuentra un índice que no esté ya en el individuo
            candidatos = set(range(N_POOL)) - set(individuo)
            nuevo = random.choice(list(candidatos))
            individuo[i] = nuevo
    return (individuo,)


# ============ ALGORITMO PRINCIPAL ============
def main():
    print(f"Pool: {N_POOL} Pokémon")
    print(f"Rivales (equipos meta): {N_RIVALES}")
    print(f"Población: {POP_SIZE}, Generaciones: {N_GEN}")
    print(f"Batallas por evaluación: {N_RIVALES * N_BATALLAS_POR_RIVAL}")
    print()

    # Toolbox
    toolbox = base.Toolbox()
    toolbox.register("individual", crear_individuo)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", evaluar)
    toolbox.register("mate", cruzar)
    toolbox.register("mutate", mutar)
    toolbox.register("select", tools.selTournament, tournsize=3)

    # Población inicial
    pop = toolbox.population(n=POP_SIZE)

    # Estadísticas
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", lambda x: sum(v[0] for v in x) / len(x))
    stats.register("max", lambda x: max(v[0] for v in x))
    stats.register("min", lambda x: min(v[0] for v in x))

    # Hall of Fame (mejores individuos históricos)
    hof = tools.HallOfFame(1)

    # Evolución
    pop, logbook = algorithms.eaSimple(
        pop, toolbox,
        cxpb=CXPB, mutpb=MUTPB, ngen=N_GEN,
        stats=stats, halloffame=hof, verbose=True,
    )

    # Resultado final
    mejor = hof[0]
    equipo_mejor = [POOL[i]["pokemon"] for i in mejor]
    print("\n" + "=" * 50)
    print("🏆 MEJOR EQUIPO ENCONTRADO")
    print("=" * 50)
    for i, idx in enumerate(mejor):
        print(f"  {i+1}. {POOL[idx]['pokemon']:<25} [{('/'.join(POOL[idx]['types']))}]")
    print(f"\nFitness (winrate promedio vs meta): {mejor.fitness.values[0]:.1%}")

    # Guardar resultado
    out_dir = Path("data/processed")
    resultado = {
        "equipo": [POOL[i] for i in mejor],
        "fitness": mejor.fitness.values[0],
        "logbook": [
            {"gen": g, "avg": a, "max": m, "min": mn}
            for g, a, m, mn in zip(
                logbook.select("gen"),
                logbook.select("avg"),
                logbook.select("max"),
                logbook.select("min"),
            )
        ],
    }
    ruta = out_dir / "ga_result.json"
    ruta.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Resultado guardado en {ruta}")


if __name__ == "__main__":
    main()