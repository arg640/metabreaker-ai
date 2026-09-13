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
from src.fitness_components import (
    cobertura_defensiva,
    sinergia_ofensiva,
    diversidad_de_tipos,
)


# ============ CONFIGURACIÓN ============
EQUIPO_SIZE = 6
N_BATALLAS_POR_RIVAL = 3   # antes 2 → menos ruido
N_RIVALES = 7
POP_SIZE = 20              # antes 15 → más diversidad
N_GEN = 5                  # antes 4 → más tiempo                 # subimos de 2 a 4
CXPB = 0.6                 # antes 0.5
MUTPB = 0.3
SEED = 42

# Pesos del fitness (suman 1.0)
PESO_WINRATE = 0.85        # antes 0.5 → el winrate domina
PESO_COBERTURA = 0.05      # antes 0.2 → solo desempate
PESO_SINERGIA = 0.05       # antes 0.2 → solo desempate
PESO_DIVERSIDAD = 0.05     # antes 0.1 → solo desempate

random.seed(SEED)


# ============ DATOS GLOBALES ============
POOL = construir_pool()
N_POOL = len(POOL)

with open("data/processed/sample_teams.json", encoding="utf-8") as f:
    EQUIPOS_META = json.load(f)

RIVALES = EQUIPOS_META[:N_RIVALES]


# ============ GENOMA Y FITNESS ============
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)


def crear_individuo():
    """Crea un equipo aleatorio de 6 Pokémon del pool, sin repetir species_key."""
    seleccionados = []
    keys_usados = set()
    intentos = 0
    while len(seleccionados) < EQUIPO_SIZE and intentos < 1000:
        idx = random.randrange(N_POOL)
        key = POOL[idx]["species_key"]
        if key not in keys_usados:
            keys_usados.add(key)
            seleccionados.append(idx)
        intentos += 1
    return creator.Individual(seleccionados)


def evaluar(individuo):
    """
    Fitness combinado anti-meta:
      0.85 * winrate_vs_meta
    + 0.05 * cobertura_defensiva
    + 0.05 * sinergia_ofensiva
    + 0.05 * diversidad_de_tipos
    """
    equipo = [POOL[i] for i in individuo]

    # --- Componente 1: winrate vs meta ---
    winrates = []
    for rival in RIVALES:
        wr = simular_enfrentamiento(equipo, rival, n_batallas=N_BATALLAS_POR_RIVAL)
        winrates.append(wr)
    winrate_meta = sum(winrates) / len(winrates) if winrates else 0.0

    # --- Componentes 2-4: instantáneos ---
    cob = cobertura_defensiva(equipo)
    sin = sinergia_ofensiva(equipo)
    div = diversidad_de_tipos(equipo)

    # --- Fitness final ---
    fitness = (
        PESO_WINRATE * winrate_meta
        + PESO_COBERTURA * cob
        + PESO_SINERGIA * sin
        + PESO_DIVERSIDAD * div
    )

    return (fitness,)


def _gen_aleatorio_libre(keys_usados: set, ya_incluidos: list[int]) -> int | None:
    """Devuelve un índice del pool cuyo species_key no esté en uso."""
    disponibles = [
        i for i in range(N_POOL)
        if POOL[i]["species_key"] not in keys_usados and i not in ya_incluidos
    ]
    if not disponibles:
        return None
    return random.choice(disponibles)


def _deduplicar(genes: list[int]) -> list[int]:
    """Asegura que no haya species_key repetidos."""
    resultado = []
    keys_usados = set()

    for g in genes:
        key = POOL[g]["species_key"]
        if key not in keys_usados:
            keys_usados.add(key)
            resultado.append(g)
        else:
            nuevo = _gen_aleatorio_libre(keys_usados, resultado)
            if nuevo is not None:
                keys_usados.add(POOL[nuevo]["species_key"])
                resultado.append(nuevo)

    while len(resultado) < EQUIPO_SIZE:
        nuevo = _gen_aleatorio_libre(keys_usados, resultado)
        if nuevo is None:
            break
        keys_usados.add(POOL[nuevo]["species_key"])
        resultado.append(nuevo)

    return resultado


def cruzar(ind1, ind2):
    """Cruce: toma 3 genes de cada padre, deduplicando."""
    hijo1, hijo2 = [], []

    for i in range(EQUIPO_SIZE):
        if i < EQUIPO_SIZE // 2:
            hijo1.append(ind1[i])
            hijo2.append(ind2[i])
        else:
            hijo1.append(ind2[i])
            hijo2.append(ind1[i])

    hijo1 = _deduplicar(hijo1)
    hijo2 = _deduplicar(hijo2)

    ind1[:] = hijo1
    ind2[:] = hijo2
    return ind1, ind2


def mutar(individuo, indpb=0.3):
    """Mutación: reemplaza genes respetando Species Clause."""
    keys_actuales = {POOL[g]["species_key"] for g in individuo}

    for i in range(len(individuo)):
        if random.random() < indpb:
            key_vieja = POOL[individuo[i]]["species_key"]
            keys_restantes = keys_actuales - {key_vieja}
            nuevo = _gen_aleatorio_libre(keys_restantes, list(individuo))
            if nuevo is not None:
                keys_actuales.discard(key_vieja)
                keys_actuales.add(POOL[nuevo]["species_key"])
                individuo[i] = nuevo
    return (individuo,)


# ============ ALGORITMO PRINCIPAL ============
def main():
    print(f"Pool: {N_POOL} Pokémon")
    print(f"Rivales (equipos meta): {N_RIVALES}")
    print(f"Población: {POP_SIZE}, Generaciones: {N_GEN}")
    print(f"Batallas por evaluación: {N_RIVALES * N_BATALLAS_POR_RIVAL}")
    print(f"Pesos: WR={PESO_WINRATE}, COB={PESO_COBERTURA}, SIN={PESO_SINERGIA}, DIV={PESO_DIVERSIDAD}")
    print()

    # Toolbox
    toolbox = base.Toolbox()
    toolbox.register("individual", crear_individuo)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", evaluar)
    toolbox.register("mate", cruzar)
    toolbox.register("mutate", mutar)
    toolbox.register("select", tools.selTournament, tournsize=5)

    pop = toolbox.population(n=POP_SIZE)

    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", lambda x: sum(v[0] for v in x) / len(x))
    stats.register("max", lambda x: max(v[0] for v in x))
    stats.register("min", lambda x: min(v[0] for v in x))

    hof = tools.HallOfFame(1)

        # ============ EVOLUCIÓN MANUAL CON ELITISMO ============
    # Evaluar población inicial
    fitnesses = list(map(toolbox.evaluate, pop))
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit

    # Inicializar estadísticas y logbook
    logbook = tools.Logbook()
    logbook.header = ["gen", "nevals"] + (stats.fields if stats else [])
    hof.update(pop)

    # Bucle de generaciones
    for gen in range(N_GEN + 1):
        if gen == 0:
            nevals = len(pop)
        else:
            # Selección
            offspring = toolbox.select(pop, len(pop))
            offspring = [toolbox.clone(ind) for ind in offspring]

            # Cruce
            for c1, c2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < CXPB:
                    toolbox.mate(c1, c2)
                    del c1.fitness.values
                    del c2.fitness.values

            # Mutación
            for mutant in offspring:
                if random.random() < MUTPB:
                    toolbox.mutate(mutant)
                    del mutant.fitness.values

            # Evaluar solo los nuevos (fitness inválido)
            invalid = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = list(map(toolbox.evaluate, invalid))
            for ind, fit in zip(invalid, fitnesses):
                ind.fitness.values = fit

            # ELITISMO: los 2 mejores de la generación anterior sobreviven intactos
            elite = tools.selBest(pop, 2)
            offspring[-2:] = [toolbox.clone(ind) for ind in elite]

            pop[:] = offspring
            nevals = len(invalid)

        hof.update(pop)
        record = stats.compile(pop)
        logbook.record(gen=gen, nevals=nevals, **record)
        print(logbook.stream)

    # ============ RESULTADO FINAL ============
    mejor = hof[0]
    equipo_mejor = [POOL[i] for i in mejor]

    # Recalcular desglose con batallas nuevas (más justo)
    winrates_rivales = []
    for rival in RIVALES:
        wr = simular_enfrentamiento(equipo_mejor, rival, n_batallas=N_BATALLAS_POR_RIVAL)
        winrates_rivales.append(wr)
    wr_meta = sum(winrates_rivales) / len(winrates_rivales) if winrates_rivales else 0.0
    cob = cobertura_defensiva(equipo_mejor)
    sin = sinergia_ofensiva(equipo_mejor)
    div = diversidad_de_tipos(equipo_mejor)

    print("\n" + "=" * 50)
    print("🏆 MEJOR EQUIPO ENCONTRADO")
    print("=" * 50)
    for i, p in enumerate(equipo_mejor):
        tipos = "/".join(p["types"])
        print(f"  {i+1}. {p['pokemon']:<25} [{tipos}]")
    print(f"\n--- Desglose del fitness ---")
    print(f"  Winrate vs meta:     {wr_meta:.1%}  (peso {PESO_WINRATE})")
    print(f"  Cobertura defensiva: {cob:.2f}   (peso {PESO_COBERTURA})")
    print(f"  Sinergia ofensiva:   {sin:.2f}   (peso {PESO_SINERGIA})")
    print(f"  Diversidad de tipos: {div:.2f}   (peso {PESO_DIVERSIDAD})")
    print(f"\n  FITNESS TOTAL:       {mejor.fitness.values[0]:.3f}")

    # ============ GUARDAR RESULTADO ============
    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)
    resultado = {
        "equipo": equipo_mejor,
        "fitness": mejor.fitness.values[0],
        "desglose": {
            "winrate_meta": wr_meta,
            "cobertura_defensiva": cob,
            "sinergia_ofensiva": sin,
            "diversidad_tipos": div,
        },
        "pesos": {
            "winrate": PESO_WINRATE,
            "cobertura": PESO_COBERTURA,
            "sinergia": PESO_SINERGIA,
            "diversidad": PESO_DIVERSIDAD,
        },
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