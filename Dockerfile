FROM python:3.10-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    ORACLE_IC_DIR=/app/instantclient \
    LD_LIBRARY_PATH=/app/instantclient \
    OUTPUT_DIR=/app/output \
    YOLO_TELEMETRY=false

RUN set -eux; \
    sed -i -e 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' \
           -e 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        libaio1 \
        libglib2.0-0 \
        libgl1 \
        libsm6 \
        libxext6 \
        libxrender1; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements.lock ./

RUN grep -Ev '^(torch|torchvision|triton|nvidia-[^=]+)==' requirements.lock > requirements.docker.lock \
    && pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
        torch==2.8.0+cpu \
        torchvision==0.23.0+cpu \
    && pip install --no-cache-dir -r requirements.docker.lock

# Copy application source (Blueprint structure)
COPY app.py config.py ./
COPY db ./db
COPY routes ./routes
COPY service ./service
COPY utils ./utils
COPY templates ./templates
COPY static ./static
COPY model ./model
COPY instantclient_11_2 ./instantclient

RUN test -f /app/model/biaochezhajiev2.pt || (echo "Missing model/biaochezhajiev2.pt" >&2; exit 1) \
    && test -f /app/model/yoloe-26n-seg.pt  || (echo "Missing model/yoloe-26n-seg.pt"  >&2; exit 1) \
    && test -f /app/instantclient/libclntsh.so.11.1 || (echo "Missing Oracle Instant Client files under instantclient_11_2/" >&2; exit 1) \
    && mkdir -p /app/output /app/upload_tmp

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/jobs', timeout=3).read()" || exit 1

CMD ["python", "app.py"]
