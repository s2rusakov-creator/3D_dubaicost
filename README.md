# DubaiCost

Интерактивная 3D-карта «истинной стоимости» недвижимости Дубая: цена сделки +
service charge + district cooling + прочие обязательные расходы. Аналог
UrbanCost (Сеул), адаптированный под дубайские метрики.

## Стек

- **Backend + ETL**: Python 3.12, FastAPI, SQLAlchemy 2 + GeoAlchemy2, Alembic
- **БД**: PostgreSQL 16 + PostGIS 3.4 (self-hosted, контейнер)
- **Frontend**: React + TypeScript + Vite + MapLibre GL JS (3D fill-extrusion)
- **Подложка карты**: OpenFreeMap (бесплатно, без ключей и лимитов)
- Всё разворачивается одним `docker compose up` на одном VPS (~$15/мес).

## Быстрый старт

```powershell
cd C:\Users\Asa\PycharmProjects\Rasul\3D_dubaicost
Copy-Item .env.example .env
# в .env: POSTGRES_PASSWORD обязательно, ADMIN_TOKEN для review-панели
docker compose up --build -d
```

- Frontend: http://localhost:5173
- API: http://localhost:8000/docs
- Миграции применяются автоматически при старте контейнера `api`.

### Первичная загрузка данных (один раз)

```powershell
# 1. Здания пилотных районов из OSM (Marina+JLT, Downtown+Business Bay, JVC)
docker compose exec etl python -m etl.jobs.fetch_osm_buildings

# 2. Транзакции DLD + аренда + агрегация — либо ждать ночного цикла (03:00 UTC),
#    либо запустить вручную:
docker compose exec etl python -c "from etl.cron import run_all; run_all()"
```

CSV транзакций ~0.5–1 ГБ, первый прогон занимает десятки минут.

### Локальный пересбор всего (без Docker)

Один скрипт прогоняет все ETL-шаги по порядку (миграции → OSM-здания →
cooling-провайдер → коннекторы DLD + агрегация → парковка → демо-слой → POI):

```powershell
cd backend
.venv/Scripts/python.exe ../scripts/bootstrap_local.py
```

Шаги идемпотентны, повторный запуск безопасен. Нужен локальный
PostgreSQL+PostGIS и `backend/.env` с `DATABASE_URL`; DLD CSV — в `backend/raw/`
(fallback-файлы `dld_sales_fallback*.csv`, `dld_rent_fallback.csv`).

### Официальные данные из ОАЭ

Портал Dubai Pulse гео-заблокирован извне ОАЭ. Скрипт
`scripts/fetch_official_data.py` (только стандартная библиотека Python)
качает bulk CSV изнутри ОАЭ и детектит капчу/HTML-заглушку.

## Источники данных

| Источник | Что даёт | Как |
|---|---|---|
| [DLD Transactions](https://www.dubaipulse.gov.ae/data/dld-transactions/dld_transactions-open) | продажи (Sales) | bulk CSV, авто |
| [DLD Rent Contracts](https://www.dubaipulse.gov.ae/data/dld-registration/dld_rent_contracts-open) | аренда Ejari | bulk CSV, авто |
| [Service Charge Index (Mollak)](https://dubailand.gov.ae/en/eservices/service-charge-index-overview/) | service charge | вручную → `data/service_charges.csv` |
| [Empower](https://www.empower.ae/customer-care/charges-explanation/) / Tabreed | тарифы охлаждения | вручную → `data/cooling_tariffs.yaml` |
| OSM Overpass / [Overture Maps](https://overturemaps.org) | полигоны и высоты зданий | джоб `fetch_osm_buildings` / DuckDB |
| [Communities (Dubai Pulse, dm_community)](https://www.dubaipulse.gov.ae/data/dm-location/dm_community-open) | границы районов | KML→GeoJSON → `load_geo districts` |

## Структура

```
backend/
  app/          # FastAPI: api/ (map, buildings, layers, coverage, review, tiles, districts, pois)
  etl/
    connectors/ # dld_sales, dld_rent, service_charge_manual, cooling_manual, alias_overrides
    pipeline/   # matching (fuzzy + token_set-гейт + кэш), aggregate (+cooling est, anomaly), cooling
    jobs/       # fetch_osm_buildings, load_geo, compute_parking, assign_cooling_provider,
                # build_demographics, fetch_pois, rematch_all
  migrations/   # Alembic (0001 схема, 0002 demographics+pois)
data/           # ручные данные в git: cooling_tariffs.yaml, service_charges.csv, alias_overrides.yaml
scripts/        # bootstrap_local.py (пересбор), fetch_official_data.py (загрузка из ОАЭ)
frontend/
  src/layers.config.ts     # конфиг радио-слоёв зданий: новый слой = запись здесь
  src/overlays.config.ts   # конфиг оверлеев (демография, POI): цвета/подписи
  src/components/          # MapLayerPanel, MapView, BuildingCard, DistrictCard, InfoPanel, ReviewPanel
```

## Слои и оверлеи

Радио-слои зданий (активен один): Price, Rent, Service Charge, District Cooling
Fee, Parking Ratio, Built Year. Независимые оверлеи (тумблеры):

- **Диаспоры по районам** — ОРИЕНТИРОВОЧНЫЕ тенденции по преобладающим общинам
  из открытых источников (не официальная статистика; в UI помечено бейджем).
  Числа населения намеренно не заполнены — гранулярных офиц. данных нет.
- **Достопримечательности** — POI из OSM (аттракционы, молы, парки, пляжи,
  метро) круглыми маркерами с попапом.

## Принципы данных

- **«Нет данных» ≠ 0**: отсутствие строки в `building_metrics` — состояние
  no-data, здание серое.
- **Matching транзакция→здание**: score ≥ 92 — авто, 75–92 — в очередь
  ручной проверки (кнопка Admin на карте, нужен `ADMIN_TOKEN`), ниже — unmatched.
  Approve запоминает алиас — дальше мэтчится автоматически.
- **Cooling — оценка**, не счёт: формула и допущения в `etl/pipeline/cooling.py`
  и `data/cooling_tariffs.yaml`, в UI помечено "estimate".
- **Алерты** (Telegram, опционально): падение ETL-джоба, скачок объёма данных
  (>50% вниз / >3x вверх), скачок общегородской медианы цены (>30% м/м).
- Секреты только в `.env` (в git не попадает).

## API

- `GET /api/map?bbox=&layer=` — GeoJSON зданий со значением слоя
- `GET /api/tiles/{layer}/{z}/{x}/{y}.pbf` — то же векторными тайлами (ST_AsMVT)
- `GET /api/buildings/{id}` — карточка: метрики, service charge, cooling
- `GET /api/layers`, `GET /api/coverage` — покрытие и статус ETL
- `GET/POST /api/review` — очередь matching'а (заголовок `X-Admin-Token`)
- `GET /api/districts` — демо-зоны (ориентировочные диаспоры) GeoJSON
- `GET /api/pois?bbox=` — достопримечательности GeoJSON

## Статус этапов

1. ~~Этап 0: каркас~~ ✅
2. ~~Этап 1: гео-слой пилотных районов, DLD sales, слой Price~~ ✅
3. ~~Этап 2: аренда, service charge, coverage/about~~ ✅
4. ~~Этап 3: cooling estimate, true-cost карточка~~ ✅
5. ~~Этап 4: алерты-аномалии, review-UI, MVT тайлы, ночной cron~~ ✅

Дальше (по мере появления данных): скрапер Service Charge Index вместо ручного
CSV, parking ratio (нет открытого источника), исторические слои по периодам.
