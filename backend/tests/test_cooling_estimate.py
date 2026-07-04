import pytest

from etl.pipeline.cooling import CoolingAssumptions, estimate_cooling_aed_per_sqft_year


def test_empower_default_tariff():
    # Empower: 56.8 fils/RTh, 750 AED/RT/год; 400 sqft/RT, 2500 EFLH
    # demand = 750/400 = 1.875; consumption = 0.568*2500/400 = 3.55; итого 5.425
    value = estimate_cooling_aed_per_sqft_year(56.8, 750, 0, CoolingAssumptions())
    assert value == pytest.approx(5.425, abs=0.01)


def test_fuel_surcharge_applied():
    base = estimate_cooling_aed_per_sqft_year(56.8, 750, 0, CoolingAssumptions())
    with_fuel = estimate_cooling_aed_per_sqft_year(56.8, 750, 10, CoolingAssumptions())
    assert with_fuel == pytest.approx(base * 1.1, abs=0.01)


def test_none_components_are_zero():
    assert estimate_cooling_aed_per_sqft_year(None, None, None, CoolingAssumptions()) == 0.0
    only_demand = estimate_cooling_aed_per_sqft_year(None, 800, None, CoolingAssumptions())
    assert only_demand == 2.0  # 800/400


def test_custom_assumptions():
    a = CoolingAssumptions(sqft_per_rt=500, eflh_hours=2000)
    # demand = 750/500 = 1.5; consumption = 0.568*2000/500 = 2.272 -> 3.772
    assert estimate_cooling_aed_per_sqft_year(56.8, 750, 0, a) == pytest.approx(3.772, abs=0.01)
