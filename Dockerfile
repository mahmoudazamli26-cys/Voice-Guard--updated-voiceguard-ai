FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/home/voiceguard/.cache/huggingface OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then cp /run/secrets/proxy_ca /usr/local/share/ca-certificates/build-proxy.crt && update-ca-certificates; fi; \
    pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home --uid 10001 voiceguard && \
    mkdir -p /home/voiceguard/.cache/huggingface && \
    chown -R voiceguard:voiceguard /home/voiceguard/.cache
COPY --chown=voiceguard:voiceguard . ./
USER voiceguard
EXPOSE 8000
HEALTHCHECK --interval=30s --start-period=180s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers", "--no-access-log"]
