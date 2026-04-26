ARG BASE_IMAGE=python:3.10-slim-bullseye
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    ORACLE_IC_DIR=/app/instantclient_11_2 \
    LD_LIBRARY_PATH=/app/instantclient_11_2 \
    ORACLE_USE_THICK_MODE=true \
    OUTPUT_DIR=/data/output \
    RESULTS_DIR=/data/output/_results \
    SQLITE_DB_PATH=/data/jobs.sqlite3 \
    UPLOAD_TEMP_DIR=/data/upload_tmp \
    FACE_DATA_DIR=/data/face_data \
    DATASETS_DIR=/data/datasets \
    TRAIN_RUNS_DIR=/data/train_runs \
    YOLO_TELEMETRY=false

RUN set -eux; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i -e 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' \
               -e 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list; \
    fi; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i -e 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' \
               -e 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources; \
    fi; \
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
COPY wheels/clip-1.0-py3-none-any.whl ./wheels/

RUN grep -Ev '^(torch|torchvision|triton|nvidia-[^=]+)==' requirements.lock > requirements.docker.lock \
    && /usr/local/bin/python -m pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
        torch==2.8.0+cpu \
        torchvision==0.23.0 \
    && /usr/local/bin/python -m pip install --no-cache-dir -r requirements.docker.lock

# Copy application source (module-oriented structure)
COPY app.py ./
COPY worker.py ./
COPY shared ./shared
COPY modules ./modules
COPY templates ./templates
COPY static ./static
COPY model ./model
COPY instantclient_11_2 ./instantclient_11_2

RUN test -f /app/model/biaochezhajiev2.pt || (echo "Missing model/biaochezhajiev2.pt" >&2; exit 1) \
    && test -f /app/model/yolov8s-worldv2.pt || (echo "Missing model/yolov8s-worldv2.pt" >&2; exit 1) \
    && test -f /app/model/det_10g.onnx || (echo "Missing model/det_10g.onnx" >&2; exit 1) \
    && test -f /app/model/w600k_r50.onnx || (echo "Missing model/w600k_r50.onnx" >&2; exit 1) \
    && test -f /app/static/dist/tailwind.css || (echo "Missing built Tailwind CSS at static/dist/tailwind.css; run npm run build:css before docker build" >&2; exit 1) \
    && test -f /app/instantclient_11_2/libclntsh.so.11.1 || (echo "Missing Linux Oracle Instant Client under instantclient_11_2/" >&2; exit 1) \
    && mkdir -p /data/output /data/upload_tmp /data/face_data /data/datasets /data/train_runs

VOLUME ["/data"]

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD /usr/local/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/healthz', timeout=3).read()" || exit 1

CMD ["/usr/local/bin/python", "app.py"]
