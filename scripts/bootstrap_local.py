#!/usr/bin/env python3
"""Полный локальный пересбор данных DubaiCost с нуля (без Docker).

Запускать из виртуального окружения backend, где установлены зависимости
и настроен backend/.env (DATABASE_URL на локальный PostgreSQL+PostGIS).

    cd backend
    .venv/Scripts/python.exe ../scripts/bootstrap_local.py

Шаги идемпотентны (upsert/дедуп) — повторный запуск безопасен.
Предполагает, что DLD CSV лежат в backend/raw/ (см. README: fallback-файлы),
иначе коннекторы DLD скачивают с DLD_*_CSV_URL или пропускаются.
"""
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"

STEPS = [
    ("Миграции БД", ["-m", "alembic", "upgrade", "head"]),
    ("OSM-здания (11 районов)", ["-m", "etl.jobs.fetch_osm_buildings"]),
    ("Cooling-провайдер (зоны Empower)", ["-m", "etl.jobs.assign_cooling_provider"]),
    ("Коннекторы DLD + агрегация", ["-c", "from etl.cron import run_all; run_all()"]),
    ("Парковка из транзакций", ["-m", "etl.jobs.compute_parking"]),
    ("Демо-слой районов", ["-m", "etl.jobs.build_demographics"]),
    ("Достопримечательности (POI)", ["-m", "etl.jobs.fetch_pois"]),
]


def main() -> int:
    print(f"Bootstrap DubaiCost — {len(STEPS)} шагов\n")
    for i, (name, args) in enumerate(STEPS, 1):
        print(f"[{i}/{len(STEPS)}] {name} ...")
        result = subprocess.run([sys.executable, *args], cwd=BACKEND)
        if result.returncode != 0:
            print(f"\n[ОШИБКА] Шаг '{name}' завершился с кодом {result.returncode}.")
            print("Проверь вывод выше. Остальные шаги пропущены.")
            return result.returncode
        print(f"[{i}/{len(STEPS)}] {name} — готово\n")
    print("Готово. Запусти backend (uvicorn) и frontend (npm run dev).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
