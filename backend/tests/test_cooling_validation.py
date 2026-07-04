from etl.connectors.cooling_manual import validate_entry


def valid_entry(**overrides) -> dict:
    entry = {
        "provider": "empower",
        "scope": "provider_default",
        "effective_from": "2026-01-01",
        "source_note": "https://example.com",
        "entered_by": "tester",
    }
    entry.update(overrides)
    return entry


def test_valid_entry_passes():
    assert validate_entry(valid_entry()) == []


def test_missing_source_note_fails():
    errors = validate_entry(valid_entry(source_note=None))
    assert any("source_note" in e for e in errors)


def test_missing_entered_by_fails():
    errors = validate_entry(valid_entry(entered_by=""))
    assert any("entered_by" in e for e in errors)


def test_bad_scope_fails():
    errors = validate_entry(valid_entry(scope="city"))
    assert any("scope" in e for e in errors)


def test_building_scope_requires_name():
    errors = validate_entry(valid_entry(scope="building"))
    assert any("building_name" in e for e in errors)


def test_building_scope_with_name_passes():
    assert validate_entry(valid_entry(scope="building", building_name="Marina Heights")) == []
