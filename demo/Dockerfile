# Hugging Face Spaces용 이미지 (sdk: docker).
#
# HF Spaces의 Streamlit SDK는 지원 버전이 제한적이고, 설정 레퍼런스 문서에는
# streamlit이 SDK 목록에서 빠져 있다. Docker SDK로 올리면 우리가 고정한 버전이
# 그대로 뜨므로 이 경로를 기본으로 삼는다.
#
# Streamlit Spaces는 8501 포트만 허용하므로 그대로 맞춘다.
# requirements.txt의 numpy==2.5.2 는 Python >= 3.12 를 요구한다.
# 베이스를 3.11로 두면 pip install 단계에서 바로 실패한다.
FROM python:3.12-slim

# HF Spaces는 컨테이너를 uid 1000으로 실행한다.
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

EXPOSE 8501

# HEALTHCHECK은 두지 않는다 — slim 이미지에 curl이 없고, HF Spaces는
# Docker HEALTHCHECK을 요구하지 않는다. 상태는 /_stcore/health 로 확인하면 된다.

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
