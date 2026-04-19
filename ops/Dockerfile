FROM python:3.10-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    ORACLE_IC_DIR=/app/instantclient \
    LD_LIBRARY_PATH=/app/instantclient \
    SQLITE_DB_PATH=/app/data/jobs.sqlite3 \
    OUTPUT_DIR=/app/output \
    RESULTS_DIR=/app/output/_results \
    DATASETS_DIR=/app/datasets \
    TRAIN_RUNS_DIR=/app/train_runs \
    UPLOAD_TEMP_DIR=/app/upload_tmp \
    FACE_DATA_DIR=/app/face_data \
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

# Copy application source (module-oriented structure)
COPY app.py ./
COPY worker.py ./
COPY shared ./shared
COPY modules ./modules
COPY templates ./templates
COPY static ./static
COPY model ./model
COPY instantclient_11_2 ./instantclient

RUN test -f /app/model/biaochezhajiev2.pt || (echo "Missing model/biaochezhajiev2.pt" >&2; exit 1) \
    && test -f /app/model/yolov8s-worldv2.pt || (echo "Missing model/yolov8s-worldv2.pt" >&2; exit 1) \
    && test -f /app/instantclient/libclntsh.so.11.1 || (echo "Missing Oracle Instant Client files under instantclient_11_2/" >&2; exit 1) \
    && mkdir -p /app/data /app/output /app/output/_results /app/datasets /app/face_data /app/train_runs /app/upload_tmp

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/healthz', timeout=3).read()" || exit 1

CMD ["python", "app.py"]
