from etl.pipeline.matching import (
    AUTO_THRESHOLD,
    REVIEW_THRESHOLD,
    BuildingMatcher,
    classify_score,
    is_low_quality_alias,
    normalize_name,
)


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    """Минимальная заглушка Session для BuildingMatcher.__init__."""

    def __init__(self, rows):
        self._rows = rows

    def execute(self, *args, **kwargs):
        return _FakeResult(self._rows)


def test_classify_thresholds():
    assert classify_score(100) == "auto"
    assert classify_score(AUTO_THRESHOLD) == "auto"
    assert classify_score(AUTO_THRESHOLD - 0.1) == "review"
    assert classify_score(REVIEW_THRESHOLD) == "review"
    assert classify_score(REVIEW_THRESHOLD - 0.1) == "unmatched"
    assert classify_score(0) == "unmatched"


def test_normalize_name():
    assert normalize_name("Marina  Heights") == "marina heights"
    assert normalize_name("MARINA-HEIGHTS") == "marina heights"
    assert normalize_name("  Burj Vista 1 ") == "burj vista 1"


def test_low_quality_alias_filtered():
    # Короткие/общие/кодовые алиасы ловят посторонние транзакции — отсеиваем
    assert is_low_quality_alias("A")
    assert is_low_quality_alias("01")
    assert is_low_quality_alias("G24")
    assert is_low_quality_alias("Residence")
    assert is_low_quality_alias("Tower")
    # Нормальные названия проходят
    assert not is_low_quality_alias("Marina Pinnacle")
    assert not is_low_quality_alias("Burj Khalifa")


def test_matcher_exact_and_generic_filter():
    rows = [
        ("Princess Tower", 11),
        ("Marina Pinnacle", 10),
        ("Residence", 99),  # generic — должен быть отфильтрован из пула
    ]
    m = BuildingMatcher(_FakeDB(rows))
    assert m.match("Princess Tower").status == "auto"
    assert m.match("Princess Tower").building_id == 11
    # Generic-алиас не участвует в matching — разные "...Residence" не липнут к 99
    r = m.match("Prestige One Residences")
    assert r.building_id != 99


def test_combined_scorer_rejects_brand_number_falsematch():
    # "Azizi Venice 6" не должен авто-матчиться на "DIC Building 6" (общий только "6")
    rows = [("DIC Building 6 (Oracle)", 6), ("Princess Tower", 11)]
    m = BuildingMatcher(_FakeDB(rows))
    r = m.match("Azizi Venice 6")
    assert r.status != "auto" or r.building_id != 6
