"""실 임상 데이터(CDC ILINet) 기반 감염병 조기경보 예측 모듈.

self-target proxy 라벨(Cohen κ=0.058)을 실제 임상 ground truth(CDC ILINet wILI)로
교체하고, 누수 없는 walk-forward(시즌 단위) 검증으로 1–4주 선행 예측 +
유행 개시 조기경보(리드타임)를 산출한다.

서브모듈:
- epidata_client : Delphi Epidata(CDC ILINet/covidcast) 다운로드 + 디스크 캐시
- dataset        : 주간 패널 구성 + CDC식 계절 baseline·유행개시 라벨
- features       : 누수 없는 시계열 피처 엔지니어링
- model          : per-horizon 분위 GBM 앙상블 예측기 + 기준 모델
- validate       : 시즌 단위 walk-forward 백테스트 + 임상 메트릭
"""
