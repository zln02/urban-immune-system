from src.utils import asset_path, hex_to_rgba


def test_hex_to_rgba() -> None:
    assert hex_to_rgba("#ff0000", 0.5) == "rgba(255, 0, 0, 0.5)"


def test_hex_to_rgba_with_hash() -> None:
    assert hex_to_rgba("ff0000", 0.5) == hex_to_rgba("#ff0000", 0.5)


def test_asset_path_returns_string() -> None:
    assert isinstance(asset_path("test.png"), str)


def test_asset_path_contains_assets() -> None:
    assert "assets" in asset_path("test.png")
