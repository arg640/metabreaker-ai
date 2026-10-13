.PHONY: help data train train2 index ga export test dagger-check dagger-train clean

help:
	@echo "Targets disponibles:"
	@echo "  make data          -> scrapers + parsers (Pikalytics + Showdown)"
	@echo "  make train         -> entrena bc_model.pt (seed 47)"
	@echo "  make train2        -> entrena bc_model_2.pt (seed 123)"
	@echo "  make index         -> construye expert_index.pkl"
	@echo "  make ga            -> corre el algoritmo genetico"
	@echo "  make export        -> exporta Top 5 a Showdown"
	@echo "  make dagger-check  -> diagnostico de datos DAgger"
	@echo "  make dagger-train  -> fine-tuning con DAgger"
	@echo "  make test          -> corre pytest"
	@echo "  make clean         -> borra checkpoint del GA"

data:
	python src/scraper_full.py
	python src/parse_api.py
	python src/scraper_pikalytics.py
	python src/parse_html.py
	node scripts_fetch_abilities.js
	node scripts_fetch_base_stats.js

train:
	python -m scripts.bc_train --seed 47 --output models_bc/bc_model.pt

train2:
	python -m scripts.bc_train --seed 123 --output models_bc/bc_model_2.pt

index:
	python -m scripts.build_expert_index

ga:
	python -u -m src.ga

export:
	python -m src.export_team

dagger-check:
	python -m scripts.dagger_check

dagger-train:
	python -m scripts.dagger_retrain

test:
	pytest -v

clean:
	powershell -Command "Remove-Item -Force -ErrorAction SilentlyContinue data\processed\checkpoint.json"
	powershell -Command "Remove-Item -Force -ErrorAction SilentlyContinue data\ga_logs\winner_logs.jsonl"