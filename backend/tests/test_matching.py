from etl.pipeline.matching import (
    AUTO_THRESHOLD,
    REVIEW_THRESHOLD,
    classify_score,
    normalize_name,
)


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
