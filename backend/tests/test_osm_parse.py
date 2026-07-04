from etl.jobs.fetch_osm_buildings import (
    element_to_feature,
    parse_height,
    parse_year,
    way_to_polygon,
)

SQUARE = [
    {"lat": 25.0, "lon": 55.0},
    {"lat": 25.0, "lon": 55.001},
    {"lat": 25.001, "lon": 55.001},
    {"lat": 25.001, "lon": 55.0},
    {"lat": 25.0, "lon": 55.0},
]


def test_parse_height():
    assert parse_height("123") == 123
    assert parse_height("123.5 m") == 123.5
    assert parse_height(None) is None
    assert parse_height("tall") is None


def test_parse_year():
    assert parse_year("1998") == 1998
    assert parse_year("2005-06-01") == 2005
    assert parse_year("1200") is None  # неправдоподобно
    assert parse_year(None) is None


def test_way_to_polygon_closed_square():
    poly = way_to_polygon(SQUARE)
    assert poly is not None
    assert poly.is_valid


def test_way_to_polygon_open_way_rejected():
    assert way_to_polygon(SQUARE[:-1]) is None


def test_element_to_feature_way():
    el = {
        "type": "way",
        "id": 42,
        "geometry": SQUARE,
        "tags": {"name": "Test Tower", "height": "150 m", "building:levels": "40",
                 "start_date": "2012"},
    }
    feat = element_to_feature(el)
    assert feat is not None
    assert feat["name"] == "Test Tower"
    assert feat["height"] == 150
    assert feat["year"] == 2012
    assert feat["osm_ref"] == "osm:way/42"


def test_element_to_feature_node_skipped():
    assert element_to_feature({"type": "node", "id": 1}) is None
