# prototype/ — 공모전 원본 Streamlit (아카이브)

> **성격**: 아카이브 레퍼런스. 수정 금지. 디자인·UX 기준선.
> **복원일**: 2026-04-22 (커밋 09b617a 에서 삭제됐다가 재복원)
> **원본**: 2026-03 공모전 대상 수상 당시 제출본 (1,408 줄 단일 파일)

---

## 🎯 왜 복원했나

- **"대시보드를 프로토타입 그대로 따라가는 게 맞다"** 는 결정 (박진영, 2026-04-22)
- `src/` 모듈화판이 일부 분기돼 프로토타입 디자인·구조 감각이 흐려짐
- 공모전 제안서 구조도 `prototype/ (아카이브)` 로 명시되어 있었음

---

## 🔀 `prototype/` vs `src/` 역할 분담

| 항목 | `prototype/` | `src/` |
|---|---|---|
| 성격 | **아카이브 (수정 금지)** | **현재 운영** |
| 구조 | 단일 파일 `app.py` (1,408 줄) | 모듈화 (`tabs/` · `map/` · `components/` · `styles.py`) |
| 색상 | 기존 Tailwind 팔레트 | Okabe-Ito CUD (색맹 안전) |
| 데이터 | 하드코딩 시뮬레이션 | JSON 동적 로드 (`ml/outputs/`) |
| 용도 | 디자인·UX 레퍼런스 | 발표·실운영 |
| 실행 | `streamlit run prototype/app.py` | `streamlit run src/app.py` |

---

## ⚖️ 분기 정책

`src/` 개발 시 **UI/UX 의심나면 `prototype/app.py` 를 참조** 한다.

- 레이아웃·톤·마진: prototype 기준
- 색상·접근성: src 기준 (Okabe-Ito 팔레트 우선)
- 데이터 구조: src 기준 (JSON 로드)
- 컴포넌트 이름: src 기준 (모듈 분리)

수정 필요 시 `src/` 에서만 수정. `prototype/` 은 히스토리.

---

## 🚀 실행

```bash
cd ~/urban-immune-system
source .venv/bin/activate
pip install -r prototype/requirements.txt
streamlit run prototype/app.py --server.port 8502
# src/ 와 포트 분리 (8501 vs 8502)
```

---

## 📚 관련

- 삭제 커밋: `09b617a` (2026-04-21)
- 복원 커밋: 2026-04-22 `restore(prototype)` 계열
- 후속 개발: `src/` 에서 이어감
- Streamlit 레퍼런스: `prototype/app.py:1-200` (색상 · 상단 헤더 · 레이아웃)
