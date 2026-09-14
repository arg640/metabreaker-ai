# src/ga.py
"""
Algoritmo Genético para evolucionar equipos anti-meta.
- Sistema de guardado: ga_result.json, ga_history.json, ga_elites.json
- Warm start: reinyecta elites históricos al inicio de cada corrida
- Top 5 mostrado en el resultado final, ordenado por fitness recalculado
"""
import json
import random
from datetime import datetime
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
N_BATALLAS_POR_RIVAL = 3
N_RIVALES = 7
POP_SIZE = 20
N_GEN = 5
CXPB = 0.6
MUTPB = 0.3
SEED = 42

# Pesos del fitness (suman 1.0)
PESO_WINRATE = 0.85
PESO_COBERTURA = 0.05
PESO_SINERGIA = 0.05
PESO_DIVERSIDAD = 0.05

# Warm start
USE_WARM_START = True
WARM_START_N = 3

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
    """Fitness combinado anti-meta."""
    equipo = [POOL[i] for i in individuo]

    winrates = []
    for rival in RIVALES:
        wr = simular_enfrentamiento(equipo, rival, n_batallas=N_BATALLAS_POR_RIVAL)
        winrates.append(wr)
    winrate_meta = sum(winrates) / len(winrates) if winrates else 0.0

    cob = cobertura_defensiva(equipo)
    sin = sinergia_ofensiva(equipo)
    div = diversidad_de_tipos(equipo)

    fitness = (
        PESO_WINRATE * winrate_meta
        + PESO_COBERTURA * cob
        + PESO_SINERGIA * sin
        + PESO_DIVERSIDAD * div
    )

    return (fitness,)


def _gen_aleatorio_libre(keys_usados: set, ya_incluidos: list[int]) -> int | None:
    disponibles = [
        i for i in range(N_POOL)
        if POOL[i]["species_key"] not in keys_usados and i not in ya_incluidos
    ]
    if not disponibles:
        return None
    return random.choice(disponibles)


def _deduplicar(genes: list[int]) -> list[int]:
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

    toolbox = base.Toolbox()
    toolbox.register("individual", crear_individuo)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", evaluar)
    toolbox.register("mate", cruzar)
    toolbox.register("mutate", mutar)
    toolbox.register("select", tools.selTournament, tournsize=3)

    pop = toolbox.population(n=POP_SIZE)

    # Warm start
    ruta_elites = Path("data/processed/ga_elites.json")
    if ruta_elites.exists() and USE_WARM_START:
        elites_data = json.loads(ruta_elites.read_text(encoding="utf-8"))
        n_reinyectar = min(len(elites_data), WARM_START_N)
        for i in range(n_reinyectar):
            genoma = elites_data[i]["genoma"]
            if len(genoma) == EQUIPO_SIZE and all(0 <= g < N_POOL for g in genoma):
                pop[i] = creator.Individual(genoma)
        print(f"🔥 Warm start: {n_reinyectar} elites reinyectados\n")

    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", lambda x: sum(v[0] for v in x) / len(x))
    stats.register("max", lambda x: max(v[0] for v in x))
    stats.register("min", lambda x: min(v[0] for v in x))

    hof = tools.HallOfFame(5)

    # Evolución manual con elitismo
    fitnesses = list(map(toolbox.evaluate, pop))
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit

    logbook = tools.Logbook()
    logbook.header = ["gen", "nevals"] + (stats.fields if stats else [])
    hof.update(pop)

    for gen in range(N_GEN + 1):
        if gen == 0:
            nevals = len(pop)
        else:
            offspring = toolbox.select(pop, len(pop))
            offspring = [toolbox.clone(ind) for ind in offspring]

            for c1, c2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < CXPB:
                    toolbox.mate(c1, c2)
                    del c1.fitness.values
                    del c2.fitness.values

            for mutant in offspring:
                if random.random() < MUTPB:
                    toolbox.mutate(mutant)
                    del mutant.fitness.values

            invalid = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = list(map(toolbox.evaluate, invalid))
            for ind, fit in zip(invalid, fitnesses):
                ind.fitness.values = fit

            elite = tools.selBest(pop, 2)
            offspring[-2:] = [toolbox.clone(ind) for ind in elite]

            pop[:] = offspring
            nevals = len(invalid)

        hof.update(pop)
        record = stats.compile(pop)
        logbook.record(gen=gen, nevals=nevals, **record)
        print(logbook.stream)

    # ============ RESULTADO FINAL ============
    # Tomamos top 10 candidatos y reordenamos por fitness recalculado
    candidatos = tools.selBest(pop, min(10, len(pop)))

    print("\n" + "=" * 60)
    print("🏆 TOP 5 EQUIPOS ENCONTRADOS")
    print("=" * 60)

    resultados_top5 = []
    for ind in candidatos:
        equipo = [POOL[i] for i in ind]

        # Recalcular winrate con batallas nuevas (más honesto)
        winrates_rivales = []
        for rival in RIVALES:
            wr = simular_enfrentamiento(equipo, rival, n_batallas=N_BATALLAS_POR_RIVAL)
            winrates_rivales.append(wr)
        wr_meta = sum(winrates_rivales) / len(winrates_rivales) if winrates_rivales else 0.0
        cob = cobertura_defensiva(equipo)
        sin = sinergia_ofensiva(equipo)
        div = diversidad_de_tipos(equipo)

        # Fitness recalculado con batallas nuevas (más justo que el de la evolución)
        fitness_recalculado = (
            PESO_WINRATE * wr_meta
            + PESO_COBERTURA * cob
            + PESO_SINERGIA * sin
            + PESO_DIVERSIDAD * div
        )

        resultados_top5.append({
            "equipo": equipo,
            "fitness": fitness_recalculado,
            "fitness_evolucion": ind.fitness.values[0],
            "desglose": {
                "winrate_meta": wr_meta,
                "cobertura_defensiva": cob,
                "sinergia_ofensiva": sin,
                "diversidad_tipos": div,
            },
        })

    # Reordenar por fitness recalculado (más honesto)
    resultados_top5.sort(key=lambda x: x["fitness"], reverse=True)
    resultados_top5 = resultados_top5[:5]

    # Asignar ranks y mostrar
    for i, r in enumerate(resultados_top5, 1):
        r["rank"] = i
        equipo = r["equipo"]
        d = r["desglose"]
        print(f"\n--- #{i} ---")
        for j, p in enumerate(equipo):
            tipos = "/".join(p["types"])
            print(f"  {j+1}. {p['pokemon']:<25} [{tipos}]")
        print(f"  Winrate: {d['winrate_meta']:.1%} | Cobertura: {d['cobertura_defensiva']:.2f} | "
              f"Sinergia: {d['sinergia_ofensiva']:.2f} | Diversidad: {d['diversidad_tipos']:.2f}")
        print(f"  FITNESS (recalculado): {r['fitness']:.3f}  |  FITNESS (evolución): {r['fitness_evolucion']:.3f}")

    mejor = resultados_top5[0]
    equipo_mejor = mejor["equipo"]
    wr_meta_mejor = mejor["desglose"]["winrate_meta"]

    # ============ GUARDAR RESULTADOS ============
    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    resultado = {
        "timestamp": datetime.now().isoformat(),
        "equipo": equipo_mejor,
        "fitness": mejor["fitness"],
        "fitness_evolucion": mejor["fitness_evolucion"],
        "top5": resultados_top5,
        "desglose": mejor["desglose"],
        "config": {
            "POP_SIZE": POP_SIZE,
            "N_GEN": N_GEN,
            "N_RIVALES": N_RIVALES,
            "N_BATALLAS_POR_RIVAL": N_BATALLAS_POR_RIVAL,
            "CXPB": CXPB,
            "MUTPB": MUTPB,
            "SEED": SEED,
            "PESO_WINRATE": PESO_WINRATE,
            "PESO_COBERTURA": PESO_COBERTURA,
            "PESO_SINERGIA": PESO_SINERGIA,
            "PESO_DIVERSIDAD": PESO_DIVERSIDAD,
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

    # Historial acumulativo
    ruta_historial = out_dir / "ga_history.json"
    if ruta_historial.exists():
        historial = json.loads(ruta_historial.read_text(encoding="utf-8"))
    else:
        historial = []

    resumen = {
        "timestamp": resultado["timestamp"],
        "fitness": resultado["fitness"],
        "winrate_meta": wr_meta_mejor,
        "config": resultado["config"],
        "top5_nombres": [
            {"rank": r["rank"], "equipo": [p["pokemon"] for p in r["equipo"]], "fitness": r["fitness"]}
            for r in resultados_top5
        ],
    }
    historial.append(resumen)
    ruta_historial.write_text(json.dumps(historial, indent=2, ensure_ascii=False), encoding="utf-8")

    # Elites para warm start
    ruta_elites = out_dir / "ga_elites.json"
    if ruta_elites.exists():
        elites_previos = json.loads(ruta_elites.read_text(encoding="utf-8"))
    else:
        elites_previos = []

    nuevos_elites = [
        {
            "genoma": [POOL.index(p) if p in POOL else i for i, p in enumerate(r["equipo"])],
            "fitness": r["fitness"],
            "nombres": [p["pokemon"] for p in r["equipo"]],
        }
        for r in resultados_top5
    ]

    todos = elites_previos + nuevos_elites
    todos.sort(key=lambda x: x["fitness"], reverse=True)
    elites_finales = todos[:10]

    ruta_elites.write_text(
        json.dumps(elites_finales, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n✅ Resultado: {ruta}")
    print(f"✅ Historial: {ruta_historial} ({len(historial)} corridas)")
    print(f"✅ Elites: {ruta_elites} ({len(elites_finales)} mejores históricos)")


if __name__ == "__main__":
    main()