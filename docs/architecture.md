# Architecture

## Flow

1. `pipeline/collectors`가 외부 소스를 수집합니다.
2. 수집 데이터는 Kafka와 TimescaleDB로 전달됩니다.
3. `ml/`이 이상탐지, 예측, 리포트 생성을 담당합니다.
4. `backend/`가 신호와 리포트를 API로 제공합니다.
5. `frontend/`가 지도와 차트로 시각화합니다.
