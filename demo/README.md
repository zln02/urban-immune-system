---
title: Urban Immune System Demo
emoji: 🦠
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8501
pinned: false
license: mit
short_description: 비의료 3계층 신호로 감염병을 선행 탐지하는 조기경보 시스템 데모 (합성 데이터)
---

# Urban Immune System — 합성 데이터 데모

> ⚠️ **이 데모의 모든 수치는 합성(synthetic) 데이터입니다.**
> 실제 약국 판매·하수 검사·검색량 데이터가 아니며, 실제 감염병 위험도를
> 나타내지 않습니다. 방역·의료 판단에 사용할 수 없습니다.

약국 OTC 구매 · 하수 바이오마커 · 검색 트렌드라는 **비의료 신호 3계층**을
교차검증해 감염병을 선행 탐지하는 시스템이 **어떻게 동작하는지** 보여주는
데모다. 성능을 주장하지 않는다.

## 무엇을 볼 수 있나

| 탭 | 내용 |
|---|---|
| 3계층 신호 | 임상 신고 곡선보다 먼저 움직이는 3개 계층 (L1 8주 · L2 2주 · L3 3주 선행) |
| 융합 위험도 · 경보 | 3계층 가중 융합과 **Gate B 교차검증** — 게이트가 막은 오경보를 X 표시로 구분 |
| 지역 현황 | 17개 시·도 위험도 랭킹 |
| 이 데모의 한계 | 데모가 하지 않는 것들 |

**핵심은 게이트다.** 언론 보도로 검색량만 폭증하거나 할인 행사로 약국 판매만
뛰는 경우, 단일 신호만 믿는 방식은 오경보를 낸다 — Google Flu Trends가
과대예측으로 실패한 지점이다. 이 데모는 그런 단일 계층 급등을 일부러 심어 두고,
최소 2개 계층이 함께 올라야 경보를 내는 게이트가 그것을 어떻게 걸러내는지
보여준다.

게이트 파라미터는 실제 백테스트 설정과 같은 값을 쓴다
(최소 통과 계층 2 · 계층 임계 30 · 경보 임계 75).

## 이 데모가 하지 않는 것

- **실데이터를 읽지 않는다.** 고정 시드로 만든 난수 곡선이다. DB·외부 API·
  실데이터 파일 어디에도 접근하지 않는다.
- **모델이 없다.** 실제 시스템은 XGBoost 주모델 + TFT 해석성 보조를 쓰지만,
  이 데모에는 학습된 모델이 들어 있지 않다. 가중 합산만 한다.
- **여기 뜨는 경보 건수는 성능 지표가 아니다.**

실제 검증 결과(17개 시·도 walk-forward 백테스트)와 그 한계는 본 저장소
README의 "검증 결과" · "한계와 정직성" 절에 있다. 숫자를 인용하려면 그쪽을
봐야 한다.

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 배포 메모

이 디렉터리는 **Hugging Face Space 저장소의 루트로 그대로 올리도록** 구성돼 있다.
위 YAML 블록이 Space 설정이 된다.

`sdk: docker` 를 쓰는 이유: HF의 Streamlit SDK는 지원 버전이 제한적이고,
[Spaces 설정 레퍼런스](https://huggingface.co/docs/hub/spaces-config-reference)의
`sdk` 목록에는 streamlit이 빠져 있다. Docker로 올리면 `requirements.txt` 에
고정한 버전이 그대로 뜬다. Streamlit SDK로 바꾸고 싶다면 YAML을 아래로 교체하고
`Dockerfile` 을 지우면 된다(단, HF가 지원하는 버전이어야 한다).

```yaml
sdk: streamlit
sdk_version: <HF가 지원하는 버전>
app_file: app.py
```

Streamlit Community Cloud에 올릴 경우에는 Docker가 필요 없고,
저장소 `zln02/urban-immune-system` · 브랜치 `main` · main file path
`demo/app.py` 로 지정하면 된다.

> HF Streamlit Space는 8501 포트만 허용한다. `.streamlit/config.toml` 에서
> 포트를 덮어쓰지 않도록 주의할 것 — 이 저장소의 설정은 테마와 headless만 건드린다.

## 구성

```
demo/
├── app.py            # Streamlit 앱 (저장소 운영 코드 import 0건)
├── synthetic.py      # 합성 신호 생성기
├── requirements.txt  # 데모 전용 의존성 4개
├── Dockerfile        # HF Spaces(sdk: docker)용
└── .streamlit/       # 테마 (포트 미지정)
```

전체 코드: https://github.com/zln02/urban-immune-system
