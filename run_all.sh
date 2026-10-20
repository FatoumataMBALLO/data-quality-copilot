#!/usr/bin/env bash
# Reconstruit tout le projet de zéro : base, anomalies, contrôles, explications, tests.
set -e

echo "=== 1/6 Ingestion ==="
rm -f data/dq.duckdb
python src/ingest.py > /dev/null

echo "=== 2/6 Injection d'anomalies ==="
python src/inject.py > /dev/null

echo "=== 3/6 Exécution des règles ==="
python src/run_checks.py

echo "=== 4/6 Origine des anomalies ==="
python src/origin.py > /dev/null

echo "=== 5/6 Explications ==="
python src/explain.py

echo "=== 6/6 Tests ==="
python -m pytest -q