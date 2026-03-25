# Urban Immune System — AI 감염병 조기경보

## Commands
```bash
cd /home/wlsdud5035/urban-immune-system
source .venv/bin/activate
pip install -e ".[dev]"

# 실행
streamlit run src/app.py --server.port 8501

# 테스트
pytest

# 린트
ruff check src/ tests/
```

## Architecture
Streamlit 5탭 대시보드 (위험도 지도/시계열/상관관계/교차검증/AI리포트)

3-Layer 신호: 약국 OTC + 하수 바이오마커 + 검색 트렌드

현재 시뮬레이션 데이터, Phase 2에서 실제 API 연동 예정

## Key Paths
src/ — 메인 소스 (모듈화 완료)

src/tabs/ — 탭별 렌더링

src/map/ — Folium 지도

src/components/ — UI 컴포넌트

prototype/ — 레거시 단일파일 버전 (보존)

analysis/ — 데이터 분석 스크립트

## Code Rules
한국어 주석 유지

타입 힌트 public 함수 필수

import 순서: stdlib → third-party → local
