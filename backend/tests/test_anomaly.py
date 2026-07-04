from etl.connectors.util import check_volume_anomaly
from etl.pipeline.aggregate import is_median_jump


def test_volume_drop_detected():
    assert check_volume_anomaly(10_000, 4_000) is not None


def test_volume_jump_detected():
    assert check_volume_anomaly(10_000, 40_000) is not None


def test_volume_normal_ok():
    assert check_volume_anomaly(10_000, 11_000) is None
    assert check_volume_anomaly(10_000, 6_000) is None


def test_volume_no_history_ok():
    assert check_volume_anomaly(None, 1_000_000) is None
    assert check_volume_anomaly(50, 1_000_000) is None  # мало истории — не судим


def test_median_jump():
    assert is_median_jump(1000, 1400) is True
    assert is_median_jump(1000, 1100) is False
    assert is_median_jump(None, 1100) is False
    assert is_median_jump(1000, None) is False
