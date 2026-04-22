# KRDS 디자인 토큰 — 대한민국 범정부 UI/UX 디자인 시스템 v1.1.0

> 출처: https://github.com/KRDS-uiux/krds-uiux/tree/main/tokens (2026-01-12 릴리스)
> 추출: `/tmp/krds-probe/tokens/transformed_tokens.json` → 공식 `npm install krds-uiux` 와 동일
> 라이선스: 한국 디지털정부 디자인시스템 이용약관 (공공기관 납품 의무)

---

## 🎨 색상 팔레트 (Light Mode · 11~13단계)

### Primary (정부 파랑) — 11단계
| 단계 | Hex | 용도 |
|---|---|---|
| 5 | `#ecf2fe` | 배경 · 호버 제외 표면 |
| 10 | `#d8e5fd` | 선택된 행 배경 |
| 20 | `#b1cefb` | Disabled primary |
| 30 | `#86aff9` | — |
| 40 | `#4c87f6` | 3:1 대비 최소 (UI 경계) |
| **50** | **`#256ef4`** | **기본 Primary · WCAG AA 4.5:1** |
| **60** | **`#0b50d0`** | **Primary hover/active** |
| 70 | `#083891` | Focused · 진한 브랜드 |
| 80 | `#052561` | — |
| 90 | `#03163a` | 다크 모드 본문 |
| 95 | `#020f27` | 최고 대비 |

### Secondary (정부 회청) — 11단계
5=`#eef2f7` · 10=`#d6e0eb` · 20=`#bacbde` · 30=`#90b0d5` · 40=`#6b96c7` · **50=`#346fb2`** · 60=`#1c589c` · 70=`#063a74` · 80=`#052b57` · 90=`#031f3f` · 95=`#02162c`

### Gray (정부 회색) — 13단계 ⭐
| 단계 | Hex | 용도 |
|---|---|---|
| **0** | **`#ffffff`** | 페이지 배경 |
| 5 | `#f4f5f6` | 보조 표면 |
| 10 | `#e6e8ea` | 카드 채움 |
| 20 | `#cdd1d5` | 경계선 |
| 30 | `#b1b8be` | Disabled 텍스트 |
| 40 | `#8a949e` | Placeholder |
| **50** | **`#6d7882`** | 보조 텍스트 · 4.5:1 |
| 60 | `#58616a` | 활성 아이콘 |
| **70** | **`#464c53`** | 본문 보조 · 7:1 AAA |
| 80 | `#33363d` | 진한 배경 |
| 90 | `#1e2124` | 다크 표면 |
| 95 | `#131416` | 헤더·푸터 |
| **100** | **`#000000`** | 최대 대비 |

### System Colors — 11단계 × 4종

**Danger (위험/빨강)**
5=`#fdefec` · 10=`#fcdfd9` · 20=`#f7afa1` · 30=`#f48771` · 40=`#f05f42` · **50=`#de3412`** · 60=`#bd2c0f` · 70=`#8a240f` · 80=`#5c180a` · 90=`#390d05` · 95=`#260903`

**Warning (주의/노랑)**
5=`#fff3db` · 10=`#ffe0a3` · 20=`#ffc95c` · **30=`#ffb114`** · 40=`#c78500` · 50=`#9e6a00` · 60=`#8a5c00` · 70=`#614100` · 80=`#422c00` · 90=`#2e1f00` · 95=`#241800`

**Success (성공/초록)**
5=`#eaf6ec` · 10=`#d8eedd` · 20=`#a9dab4` · 30=`#7ec88e` · 40=`#3fa654` · **50=`#228738`** · 60=`#267337` · 70=`#285d33` · 80=`#1f4727` · 90=`#122b18` · 95=`#0e2012`

**Information (정보/파랑)**
5=`#e7f4fe` · 10=`#d3ebfd` · 20=`#9ed2fa` · 30=`#5fb5f7` · 40=`#2098f3` · **50=`#0b78cb`** · 60=`#096ab3` · 70=`#085691` · 80=`#053961` · 90=`#03253f` · 95=`#021a2c`

---

## 📐 Radius / Spacing

Semantic radius 체계 (primitive.number.N 참조):
- xsmall1~3 = 2 (2px)
- small1~3 = 3 (4px)
- medium1~2 = 4 (8px) / medium3~4 = 5 (12px)
- large1~2 = 6 (16px)
- xlarge1~2 = 7 (24px)
- max = 무한대 (pill)

간격은 8px 기반 그리드 (IBM Carbon 동일).

---

## 🎯 Urban Immune System 매핑 결정

우리 프로젝트는 KRDS 공식 팔레트를 **그대로 가져오지 않고 다음 2-tier 로 매핑**:

### Tier 1 — 정부 브랜드·세만틱 (KRDS 공식)
| 토큰 | KRDS 경로 | 우리 적용 |
|---|---|---|
| `--brand-primary` | `primary.60` | `#0b50d0` (링크·버튼) |
| `--brand-primary-hover` | `primary.70` | `#083891` |
| `--brand-secondary` | `secondary.60` | `#1c589c` (서브 CTA) |
| `--text-primary` | `gray.100` | `#000000` (본문) |
| `--text-secondary` | `gray.70` | `#464c53` |
| `--text-muted` | `gray.50` | `#6d7882` |
| `--border-subtle` | `gray.20` | `#cdd1d5` |
| `--surface-01` | `gray.0` | `#ffffff` |
| `--surface-02` | `gray.5` | `#f4f5f6` |

### Tier 2 — 위험도 (Okabe-Ito CUD 유지)
KRDS System Colors 가 아니라 **색맹 안전 팔레트** 유지 (한국 남성 5.9% 적록색맹 대비). 이유: KRDS Success(#228738) 와 Danger(#de3412) 가 Deuteranopia 에서 구분 약함. Okabe-Ito 가 과학적 검증됨 (Nature 권장).

| 토큰 | 값 | Level |
|---|---|---|
| `--risk-safe` | `#009E73` | 1 · ✅ |
| `--risk-caution` | `#E69F00` | 2 · 🔔 |
| `--risk-warning` | `#D55E00` | 3 · ⚠️ |
| `--risk-alert` | `#CC0000` | 4 · 🚨 |

---

## 📦 사용 방법

### HTML 컴포넌트 킷 설치
```bash
npm install krds-uiux
```

### Figma 라이브러리
https://www.figma.com/@krds

### Pretendard GOV 폰트
- CDN: `https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/woff2/PretendardVariable.woff2`
- 본 프로젝트 `globals.css` 에 이미 임포트됨

---

## 🔁 업데이트 방법

KRDS 가 새 릴리스 (v1.1.0 → v1.2.0) 냈을 때:
```bash
cd /tmp && rm -rf krds-probe && \
  git clone --depth 1 https://github.com/KRDS-uiux/krds-uiux.git krds-probe
python3 -c "
import json
t = json.load(open('/tmp/krds-probe/tokens/transformed_tokens.json'))
# ... 이 파일 재생성
"
```

혹은 `npm install krds-uiux@latest` 후 `node_modules/krds-uiux/tokens/transformed_tokens.json` 참조.
