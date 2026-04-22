# src/ 에이전트 — 김나영(Frontend, Phase1 Streamlit) 전용

## 🎯 정체성
Phase 1 데모용 Streamlit 5탭 대시보드 유지보수. **캡스톤 발표 주력 데모**이기 때문에 시뮬레이션 폴백과 실데이터 전환을 모두 매끄럽게 제공해야 한다.

## 💬 말 거는 법 (김나영이 하는 예시 지시)
- "risk_map 탭에 실데이터 API 연동 + 시뮬레이션 폴백"
- "report 탭 PDF 다운로드 버튼 추가"
- "대시보드 초기 로딩 3초 이내 최적화(`st.cache_data`)"
- "서울 25구 지도 RED/ORANGE/YELLOW/GREEN 색상 정리"
- "사이드바에 Phase 토글(시뮬/실데이터) 추가"

## 🛠 Skills
- `/commit`, `/review-pr`, `/simplify`
- 커스텀(후속): `/streamlit-run` — 8501 포트 기동 · `/ui-screenshots` — 5탭 스크린샷 캡처

## 🔌 MCP 연결
- **GitHub**: PR
- **Notion**(선택): UX 개선 아이디어 보드

## 🌿 GitHub 연계
- 브랜치: `feature/src-*` 또는 `feature/ui-*`
- PR 체크리스트:
  - [ ] `pytest tests/test_container_layout.py` 통과
  - [ ] `ruff check src/` 통과
  - [ ] 5탭 전부 시뮬 폴백 동작
  - [ ] 색상 상수(RED=#FF4B4B, ORANGE=#FFA500, YELLOW=#FFD700, GREEN=#00CC66) 유지
  - [ ] 한국어 UI 문구 일관성
- CI Job: `legacy-test`

## 🧠 자동 메모리
- 완성한 탭과 스크린샷 경로
- 사용자 피드백(발표 리허설 후)
- 시뮬/실데이터 전환 토글 상태

## 📦 상용화 기여
- **B2G 산출물**: 사용자 매뉴얼(대시보드 조작), 발표용 데모 스크립트
- **PoC 데모 시나리오**: 질병관리청 데모 시 시연할 5탭 흐름

## ✅ Definition of Done
1. `streamlit run src/app.py --server.port 8501` 부팅 성공
2. 5탭 전부 렌더 (map/timeseries/correlation/validation/report)
3. API 미연결 시에도 시뮬 폴백으로 동작
4. 로딩 < 3초
5. 스크린샷 5장 `docs/images/` 저장

## 📍 핵심 파일
- `src/app.py` — 메인 앱 (5탭 라우터)
- `src/tabs/risk_map.py` — L1: 서울 25구 위험도 지도 (Folium)
- `src/tabs/timeseries.py` — L2: 시계열 차트
- `src/tabs/correlation.py` — L3: 계층 간 상관관계
- `src/tabs/validation.py` — L4: 모델 검증 메트릭
- `src/tabs/report.py` — L5: AI 경보 리포트
- `src/map/builder.py`, `src/map/styles.py` — Folium 서울 25구 지도
- `src/components/{header,sidebar,footer,image_card}.py` — 공통 UI
- `src/config.py`, `src/utils.py`, `src/styles.py` — 설정·유틸·스타일

## 🚧 Phase 2 보조 역할
Phase 2 의 주력은 `frontend/`(Next.js). `src/` 는 캡스톤 발표 + 백업 데모용으로 유지.
