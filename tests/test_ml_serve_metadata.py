"""V11.3 — ml/serve.py TFTPredictResponse 의 demo transparency 메타 키 검증.

ml/serve.py 의 model load 가 무거우므로 schema-level 단위 테스트만 수행
(모델 추론 통합 테스트는 ML 서비스가 살아있는 환경에서 별도 수동 curl 검증).
"""

from __future__ import annotations


def test_tft_response_includes_demo_metadata_defaults() -> None:
    """TFTPredictResponse 가 새 mode/caveat/data_source 기본값을 가진다."""
    from ml.serve import TFTPredictResponse

    resp = TFTPredictResponse(
        region="서울특별시",
        horizon=7,
        predictions=[18.04],
        attention_top3=["검색트렌드", "하수기반감시", "OTC약국판매"],
    )
    dumped = resp.model_dump()

    # 기존 키 유지 — 클라이언트 의존성 보존
    assert dumped["region"] == "서울특별시"
    assert dumped["horizon"] == 7
    assert dumped["predictions"] == [18.04]
    assert dumped["attention_top3"][0] == "검색트렌드"

    # 신규 demo transparency 키 — V11.3 contract
    assert dumped["mode"] == "synthetic_demo"
    assert "Synthetic PoC input" in dumped["caveat"]
    assert "Phase 2" in dumped["caveat"]
    assert dumped["data_source"] == "_make_dataframe(seed=42)"


def test_tft_response_caveat_explicit_override_allowed() -> None:
    """발표 후 P2 refactor 시 mode/caveat 값을 명시 override 할 수 있다."""
    from ml.serve import TFTPredictResponse

    resp = TFTPredictResponse(
        region="서울특별시",
        horizon=14,
        predictions=[18.04, 18.07],
        attention_top3=["L3", "L2", "L1"],
        mode="production",
        caveat="",
        data_source="db.layer_signals + confirmed_cases",
    )
    dumped = resp.model_dump()
    assert dumped["mode"] == "production"
    assert dumped["caveat"] == ""
    assert "layer_signals" in dumped["data_source"]


def test_tft_response_pydantic_schema_keys() -> None:
    """JSON schema 가 신규 3 키를 노출 — OpenAPI/docs 일관성 보장."""
    from ml.serve import TFTPredictResponse

    schema = TFTPredictResponse.model_json_schema()
    props = schema["properties"]
    assert "mode" in props
    assert "caveat" in props
    assert "data_source" in props
    # 기존 키도 유지
    for k in ("region", "horizon", "predictions", "attention_top3"):
        assert k in props, f"기존 키 {k} 가 schema 에서 제거됨"
