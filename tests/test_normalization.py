from pipeline.collectors.normalization import min_max_normalize


def test_min_max_normalize_empty_list() -> None:
    assert min_max_normalize([]) == []


def test_min_max_normalize_constant_list() -> None:
    assert min_max_normalize([7.0, 7.0, 7.0]) == [50.0, 50.0, 50.0]


def test_min_max_normalize_scales_values() -> None:
    assert min_max_normalize([10.0, 20.0, 30.0]) == [0.0, 50.0, 100.0]
