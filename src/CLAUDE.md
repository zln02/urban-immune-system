# src/ — Streamlit 대시보드 (D1·D2 공용)

## 담당자
- **D1 김나영**: `app.py` API 분기, `tabs/` 실데이터 연동
- **D2 박정빈**: `styles.py`, `map/`, `components/` 디자인·UX

## 기술 스택
- Streamlit 1.30
- Folium 0.15
- Plotly 5.18

## 색상 시스템 — config.py에서만 변경

```python
# src/config.py
ALERT_COLORS = {
    "GREEN":  "#059669",   # 안전
    "YELLOW": "#d97706",   # 주의
    "ORANGE": "#ea580c",   # 경계 (미래 확장)
    "RED":    "#dc2626",   # 위험
}

LAYER_COLORS = {
    "L1": "#be185d",   # 약국 OTC — 마젠타
    "L2": "#047857",   # 하수도 — 청록
    "L3": "#1d4ed8",   # 검색 — 파랑
}
```
- **절대 규칙**: 컴포넌트에서 색상 직접 하드코딩 금지 — 반드시 `config.py` 참조

## D1 김나영 작업 범위

### `app.py`
- API 페이로드 유무에 따른 분기: `if data: 실데이터 렌더 else: 시뮬레이션 fallback`
- Kafka Consumer 완성 후 실데이터 탭 전환

### `tabs/`
- `tabs/overview.py` — 종합 경보 현황 (실데이터 연결)
- `tabs/layer_detail.py` — L1/L2/L3 개별 시계열
- `tabs/map_view.py` — 지도 탭 (D2와 협업)
- `tabs/forecast.py` — ML 예측 결과
- `tabs/report.py` — RAG-LLM 리포트

## D2 박정빈 작업 범위

### `styles.py`
- `apply_custom_css()` — L1/L2/L3 색상 시스템 기반 글로벌 CSS
- 경보 레벨별 배경색 클래스
- 폰트: `Noto Sans KR` 우선 적용

### `map/styles.py`
- `@keyframes pulse-ring` 맥박 애니메이션 (경보 레벨별 색상)
- 줌 레벨별 마커 크기 조정

### `map/builder.py`
- Folium 팝업: 지역명 + 경보 레벨 + 신호값 3줄 표시
- 툴팁: hover 시 composite_score 표시

### `components/`
- `components/header.py` — 경보 레벨 배너 (색상 + 아이콘)
- `components/kpi_card.py` — L1/L2/L3 지표 카드 레이아웃

## 공통 규칙
1. `print()` 금지 — `logging.getLogger(__name__)` 사용
2. Streamlit `st.session_state` 키는 `config.py`의 상수로 관리
3. Folium 지도 변경 시 `tests/test_container_layout.py` 실행 확인

## 권장 스킬 (D2)
- `/colorize` — 색상 추가
- `/animate` — 맥박 애니메이션
- `/polish` — 발표 전 마무리
- `/critique` — UX 리뷰
- `/distill` — UI 단순화
