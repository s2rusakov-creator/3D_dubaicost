"""Оценка годовых расходов на district cooling, AED/sqft/год.

Это ОЦЕНКА (estimate), а не счёт: фактическое потребление зависит от юнита.
Формула прозрачна и параметризована допущениями из cooling_tariffs.yaml:

  demand_cost   = demand_aed_per_rt_year / sqft_per_rt
  consumption   = (consumption_fils_per_rth / 100) * eflh_hours / sqft_per_rt
  total         = (demand_cost + consumption) * (1 + fuel_surcharge_pct / 100)

где sqft_per_rt — площадь на 1 тонну охлаждения (правило ~400 sqft/RT),
eflh_hours — эквивалентные часы полной нагрузки в год для Дубая.
"""
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_SQFT_PER_RT = 400.0
DEFAULT_EFLH_HOURS = 2500.0


@dataclass
class CoolingAssumptions:
    sqft_per_rt: float = DEFAULT_SQFT_PER_RT
    eflh_hours: float = DEFAULT_EFLH_HOURS


def load_assumptions(data_dir: str) -> CoolingAssumptions:
    path = Path(data_dir) / "cooling_tariffs.yaml"
    if not path.exists():
        return CoolingAssumptions()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    a = data.get("assumptions", {})
    return CoolingAssumptions(
        sqft_per_rt=float(a.get("sqft_per_rt", DEFAULT_SQFT_PER_RT)),
        eflh_hours=float(a.get("eflh_hours", DEFAULT_EFLH_HOURS)),
    )


def estimate_cooling_aed_per_sqft_year(
    consumption_fils_per_rth: float | None,
    demand_aed_per_rt_year: float | None,
    fuel_surcharge_pct: float | None,
    assumptions: CoolingAssumptions,
) -> float:
    demand = (demand_aed_per_rt_year or 0.0) / assumptions.sqft_per_rt
    consumption = (
        (consumption_fils_per_rth or 0.0) / 100.0
        * assumptions.eflh_hours / assumptions.sqft_per_rt
    )
    return round((demand + consumption) * (1 + (fuel_surcharge_pct or 0.0) / 100.0), 2)
