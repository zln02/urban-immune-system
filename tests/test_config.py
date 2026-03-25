from src.config import DISTRICTS, REGIONS, RISK_CFG


def test_regions_not_empty() -> None:
    assert len(REGIONS) > 0


def test_districts_have_required_keys() -> None:
    required_keys = {"name", "lat", "lon", "risk"}
    for district in DISTRICTS:
        assert required_keys.issubset(district.keys())


def test_districts_risk_range() -> None:
    for district in DISTRICTS:
        assert 1 <= district["risk"] <= 4


def test_risk_cfg_complete() -> None:
    assert {1, 2, 3, 4}.issubset(RISK_CFG.keys())


def test_risk_cfg_has_color_label_radius() -> None:
    required_keys = {"color", "label", "radius"}
    for level in (1, 2, 3, 4):
        assert required_keys.issubset(RISK_CFG[level].keys())
