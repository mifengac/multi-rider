ARG BASE_IMAGE=python:3.10-slim-bullseye
FROM ${BASE_IMAGE}

ARG INSTALL_ML_STACK=true

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_DEFAULT_TIMEOUT=600 \
    PIP_RETRIES=10 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    ORACLE_IC_DIR=/app/instantclient_11_2 \
    LD_LIBRARY_PATH=/app/instantclient_11_2 \
    ORACLE_USE_THICK_MODE=false \
    OUTPUT_DIR=/data/output \
    RESULTS_DIR=/data/output/_results \
    SQLITE_DB_PATH=/data/jobs.sqlite3 \
    UPLOAD_TEMP_DIR=/data/upload_tmp \
    FACE_DATA_DIR=/data/face_data \
    DATASETS_DIR=/data/datasets \
    TRAIN_RUNS_DIR=/data/train_runs \
    YOLO_TELEMETRY=false

RUN set -eux; \
    cp -a /etc/apt/sources.list /tmp/sources.list.official; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i -e 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' \
               -e 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list; \
    fi; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i -e 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' \
               -e 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources; \
    fi; \
    if ! apt-get update; then \
        echo "Tsinghua apt mirror failed, falling back to official Debian sources"; \
        cp -a /tmp/sources.list.official /etc/apt/sources.list; \
        if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
            sed -i -e 's|mirrors.tuna.tsinghua.edu.cn|deb.debian.org|g' /etc/apt/sources.list.d/debian.sources; \
        fi; \
        apt-get update; \
    fi; \
    if ! apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        libaio1 \
        libglib2.0-0 \
        libgl1 \
        libsm6 \
        libxext6 \
        libxrender1; then \
        echo "Tsinghua apt install failed, falling back to official Debian sources"; \
        cp -a /tmp/sources.list.official /etc/apt/sources.list; \
        if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
            sed -i -e 's|mirrors.tuna.tsinghua.edu.cn|deb.debian.org|g' /etc/apt/sources.list.d/debian.sources; \
        fi; \
        apt-get update; \
        apt-get install -y --no-install-recommends \
            ca-certificates \
            curl \
            git \
            libaio1 \
            libglib2.0-0 \
            libgl1 \
            libsm6 \
            libxext6 \
            libxrender1; \
    fi; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements.lock ./
COPY wheels ./wheels

RUN if [ "$INSTALL_ML_STACK" = "true" ]; then \
        grep -Ev '^(torch|torchvision|triton|nvidia-[^=]+)==' requirements.lock | grep -Fv './wheels/clip-1.0-py3-none-any.whl' > requirements.docker.lock; \
        CLIP_INSTALL_REF='git+https://github.com/openai/CLIP.git'; \
        if [ -f ./wheels/clip-1.0-py3-none-any.whl ]; then CLIP_INSTALL_REF='./wheels/clip-1.0-py3-none-any.whl'; fi; \
        mkdir -p /tmp/pytorch-whls; \
        curl -fL --retry 10 --retry-delay 5 -C - -o /tmp/pytorch-whls/torch-2.8.0+cpu-cp310-cp310-manylinux_2_28_x86_64.whl \
            'https://download.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp310-cp310-manylinux_2_28_x86_64.whl'; \
        curl -fL --retry 10 --retry-delay 5 -C - -o /tmp/pytorch-whls/torchvision-0.23.0+cpu-cp310-cp310-manylinux_2_28_x86_64.whl \
            'https://download.pytorch.org/whl/cpu/torchvision-0.23.0%2Bcpu-cp310-cp310-manylinux_2_28_x86_64.whl'; \
        /usr/local/bin/python -m pip install --no-cache-dir --no-deps \
            /tmp/pytorch-whls/torch-2.8.0+cpu-cp310-cp310-manylinux_2_28_x86_64.whl \
            /tmp/pytorch-whls/torchvision-0.23.0+cpu-cp310-cp310-manylinux_2_28_x86_64.whl; \
        /usr/local/bin/python -m pip install --no-cache-dir "$CLIP_INSTALL_REF"; \
    else \
        grep -Ev '^(torch|torchvision|triton|nvidia-[^=]+)==|^ultralytics==|^ultralytics-thop==' requirements.lock | grep -Fv './wheels/clip-1.0-py3-none-any.whl' > requirements.docker.lock; \
    fi \
    && (/usr/local/bin/python -m pip install --no-cache-dir \
        --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
        -r requirements.docker.lock \
        || (echo "Tsinghua pip mirror failed, falling back to official PyPI" \
            && /usr/local/bin/python -m pip install --no-cache-dir \
                --index-url https://pypi.org/simple \
                -r requirements.docker.lock))

# Copy application source (module-oriented structure)
RUN rm -rf /app/app.py /app/worker.py /app/shared /app/modules /app/templates /app/static /app/model /app/instantclient_11_2
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
    && if [ ! -f /app/instantclient_11_2/libclntsh.so.11.1 ]; then echo "Linux Oracle Instant Client not bundled; container will use thin mode unless ORACLE_USE_THICK_MODE=true" >&2; fi \
    && mkdir -p /data/output /data/upload_tmp /data/face_data /data/datasets /data/train_runs

VOLUME ["/data"]

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD /usr/local/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/healthz', timeout=3).read()" || exit 1

CMD ["/usr/local/bin/python", "app.py"]
