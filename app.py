import os
import io
import time
import zipfile
import logging
import threading
import uuid
from datetime import datetime
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

import requests
from typing import Optional, Tuple, List, Set
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify

# Oracle drivers
try:
    import oracledb
except Exception:
    oracledb = None
    try:
        import cx_Oracle as cx_oracle
    except Exception:
        cx_oracle = None

# YOLO
ULTR_ERR = None
try:
    from ultralytics import YOLO
except Exception as e:
    YOLO = None
    ULTR_ERR = str(e)

from PIL import Image


# ---------------------- 配置 ----------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ORACLE_HOST = os.getenv('ORACLE_HOST', '10.45.100.147')
ORACLE_PORT = int(os.getenv('ORACLE_PORT', '1521'))
ORACLE_SERVICE = os.getenv('ORACLE_SERVICE', 'yfgxpt')
ORACLE_USER = os.getenv('ORACLE_USER', 'yfzagk')
ORACLE_PASSWORD = os.getenv('ORACLE_PASSWORD', 'yfzagk')

INSTANT_CLIENT_DIR = os.getenv('ORACLE_IC_DIR', os.path.join(BASE_DIR, 'instantclient'))

MODEL_PATH = os.getenv('MODEL_PATH', os.path.join(BASE_DIR, 'model', 'biaochezhajiev2.pt'))

MAX_WORKERS = int(os.getenv('MAX_WORKERS', '8'))
CONF_THRESH = float(os.getenv('CONF_THRESH', '0.8'))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '8'))
IMGSZ = int(os.getenv('IMGSZ', '640'))
OUTPUT_DIR = os.getenv('OUTPUT_DIR', os.path.join(BASE_DIR, 'output'))
os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')


# ---------------------- Oracle 连接 ----------------------
def init_oracle_client_if_needed():
    if oracledb is not None and hasattr(oracledb, 'init_oracle_client'):
        try:
            oracledb.init_oracle_client(lib_dir=INSTANT_CLIENT_DIR)
        except Exception as e:
            logger.warning('init_oracle_client failed: %s', e)
    elif 'cx_oracle' in globals() and cx_oracle is not None:
        try:
            cx_oracle.init_oracle_client(lib_dir=INSTANT_CLIENT_DIR)
        except Exception as e:
            logger.warning('cx_Oracle init failed: %s', e)


def get_oracle_connection():
    dsn = f"{ORACLE_HOST}:{ORACLE_PORT}/{ORACLE_SERVICE}"
    if oracledb is not None:
        return oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=dsn)
    elif 'cx_oracle' in globals() and cx_oracle is not None:
        return cx_oracle.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=dsn)
    else:
        raise RuntimeError('Oracle driver not available')


def build_query_and_binds(kssj: str, jssj: str, hours: List[str]):
    # 同时取回时间字段用于按时间切分 ZIP
    sql = (
        "SELECT PIC_ABBREVIATE, TIME FROM yfgadb.T_SPY_ELCZP_XX "
        "WHERE TIME BETWEEN :kssj AND :jssj"
    )
    binds = {"kssj": kssj, "jssj": jssj}
    if hours:
        placeholders = []
        for i, h in enumerate(hours):
            key = f"h{i}"
            placeholders.append(f":{key}")
            binds[key] = h
        sql += f" AND HOUR IN ({','.join(placeholders)})"
    return sql, binds


def fetch_image_urls(kssj: str, jssj: str, hours: List[str]) -> List[Tuple[str, str]]:
    """返回 (url, timestr) 列表，timestr 统一格式为 'YYYY-MM-DD HH:MM:SS'"""
    sql, binds = build_query_and_binds(kssj, jssj, hours)
    init_oracle_client_if_needed()
    with get_oracle_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS'")
            except Exception:
                pass
            cur.execute(sql, binds)
            rows = cur.fetchall()
    out: List[Tuple[str, str]] = []
    for r in rows:
        if not r or not r[0]:
            continue
        url = r[0]
        tval = r[1] if len(r) > 1 else None
        # tval 可能是 datetime 或字符串
        if isinstance(tval, datetime):
            tstr = tval.strftime('%Y-%m-%d %H:%M:%S')
        else:
            tstr = str(tval) if tval else ''
        out.append((url, tstr))
    return out


# ---------------------- 模型与推理 ----------------------
_MODEL = None


def get_model():
    global _MODEL
    if _MODEL is None:
        if YOLO is None:
            raise RuntimeError(f'ultralytics 导入失败: {ULTR_ERR or "未安装或依赖缺失"}')
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"未找到模型文件: {MODEL_PATH}")
        _MODEL = YOLO(MODEL_PATH)
    return _MODEL


session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/requests'})


def _sanitize_zip_name(name: str) -> str:
    invalid = set('/\\:*?"<>|')
    fixed = ''.join('_' if c in invalid else c for c in name).strip()
    return fixed or 'image'


def _filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    base = os.path.basename(parsed.path) or 'image'
    base = base.split(';')[0]
    return _sanitize_zip_name(base) or 'image'


def _infer_ext_from_bytes(img_bytes: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(img_bytes))
        fmt = (img.format or '').upper()
        return {
            'JPEG': '.jpg', 'JPG': '.jpg', 'PNG': '.png', 'BMP': '.bmp',
            'WEBP': '.webp', 'GIF': '.gif', 'TIFF': '.tif'
        }.get(fmt, '.jpg')
    except Exception:
        return '.jpg'


def download_image_with_status(url: str, timeout=(6, 15)) -> Tuple[Optional[bytes], Optional[int], Optional[str]]:
    try:
        resp = session.get(url, timeout=timeout, stream=True)
        code = resp.status_code
        ctype = resp.headers.get('Content-Type') if hasattr(resp, 'headers') else None
        if 200 <= code < 300:
            return resp.content, code, ctype
        return None, code, ctype
    except requests.HTTPError as e:
        try:
            return None, e.response.status_code if e.response is not None else None, None
        except Exception:
            return None, None, None
    except Exception:
        return None, None, None


def _predict_batch(images: List[Image.Image], model, conf_thresh: float, allowed_classes: Optional[Set[int]], imgsz: int) -> List[bool]:
    results = model.predict(images, conf=min(conf_thresh, 0.25), imgsz=imgsz, verbose=False)
    out: List[bool] = []
    for res in results:
        try:
            boxes = res.boxes
            if boxes is None or boxes.conf is None:
                out.append(False)
                continue
            conf_list = boxes.conf.tolist()
            if allowed_classes is not None and hasattr(boxes, 'cls') and boxes.cls is not None:
                cls_list = [int(x) for x in boxes.cls.tolist()]
                keep = any(float(c) >= conf_thresh and k in allowed_classes for c, k in zip(conf_list, cls_list))
            else:
                keep = any(float(c) >= conf_thresh for c in conf_list)
            out.append(keep)
        except Exception:
            out.append(False)
    return out


# ---------------------- 任务与进度 ----------------------
JOBS = {}
JOBS_LOCK = threading.Lock()


def _new_job_record(total: int) -> dict:
    return {
        'id': uuid.uuid4().hex,
        'status': 'running',
        'message': '',
        'total': total,
        'processed': 0,
        'downloaded': 0,
        'kept': 0,
        'notfound': 0,
        'failed': 0,
        'start_ts': int(time.time()),
        'end_ts': None,
        'zip_bytes': None,
        'zip_path': None,
        'summary_text': '',
        'conf_thresh': CONF_THRESH,
        'batch_size': BATCH_SIZE,
        'imgsz': IMGSZ,
        'classes': None,
        'classes_raw': '',
        'owner_ip': '',
        'cancel': threading.Event(),
    }


def _summarize(job: dict) -> str:
    downloaded = job.get('downloaded') if job.get('downloaded') is not None else max(0, job['processed'] - job['notfound'] - job['failed'])
    discarded = max(0, downloaded - job['kept'])
    thr = job.get('conf_thresh', CONF_THRESH)
    lines = [
        f"总URL数: {job['total']}",
        f"已处理: {job['processed']}",
        f"下载成功: {downloaded}",
        f"置信度≥{thr}（保留）: {job['kept']}",
        f"置信度<{thr}（丢弃）: {discarded}",
        f"404 Not Found: {job['notfound']}",
        f"其他失败: {job['failed']}",
        f"开始时间: {datetime.fromtimestamp(job['start_ts']).strftime('%Y/%m/%d %H:%M:%S')}",
        f"结束时间: {datetime.fromtimestamp(job['end_ts']).strftime('%Y/%m/%d %H:%M:%S') if job['end_ts'] else ''}",
    ]
    return "\n".join(lines) + "\n"


def _run_job(job_id: str, url_and_times: List[Tuple[str, str]], conf_thresh: float, batch_size: int, imgsz: int, classes_raw: str):
    try:
        model = get_model()
        allowed_classes: Optional[Set[int]] = None
        names = getattr(model, 'names', None)
        if classes_raw and names:
            idxs: Set[int] = set()
            name_map = {str(v).lower(): k for k, v in (names.items() if isinstance(names, dict) else enumerate(names))}
            for token in [t.strip() for t in classes_raw.split(',') if t.strip()]:
                if token.isdigit():
                    idxs.add(int(token))
                else:
                    key = token.lower()
                    if key in name_map:
                        idxs.add(int(name_map[key]))
            if idxs:
                allowed_classes = idxs

        with JOBS_LOCK:
            job = JOBS[job_id]
            job['conf_thresh'] = conf_thresh
            job['batch_size'] = batch_size
            job['imgsz'] = imgsz
            job['classes_raw'] = classes_raw
            job['classes'] = allowed_classes

        # 按天切分输出多个 ZIP：key = YYYYMMDD
        def time_bin_key(tstr: str) -> str:
            try:
                if tstr:
                    dt = datetime.strptime(tstr, '%Y-%m-%d %H:%M:%S')
                    return dt.strftime('%Y%m%d')
            except Exception:
                pass
            return 'unknown'

        # 仅保留固定数量的并发 future，避免一次性提交导致内存激增
        def gen_downloads():
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                it = iter(url_and_times)
                in_flight = {}
                max_in_flight = max(1, MAX_WORKERS * 2)

                def submit_one(item):
                    (u, ts) = item
                    f = ex.submit(download_image_with_status, u)
                    in_flight[f] = (u, ts)

                # 预热
                for _ in range(max_in_flight):
                    item = next(it, None)
                    if item is None:
                        break
                    submit_one(item)

                while in_flight:
                    with JOBS_LOCK:
                        if JOBS[job_id]['cancel'].is_set():
                            return
                    done, _pending = wait(set(in_flight.keys()), return_when=FIRST_COMPLETED)
                    for fut in done:
                        u, ts = in_flight.pop(fut)
                        try:
                            data, code, _ = fut.result()
                        except Exception:
                            data, code = None, None
                        if data is None:
                            with JOBS_LOCK:
                                jb = JOBS[job_id]
                                if code == 404:
                                    jb['notfound'] += 1
                                else:
                                    jb['failed'] += 1
                        else:
                            with JOBS_LOCK:
                                JOBS[job_id]['downloaded'] += 1
                            name = _filename_from_url(u)
                            r, e = os.path.splitext(name)
                            if not e:
                                e = _infer_ext_from_bytes(data)
                                name = r + e
                            yield (name, data, ts)

                        # 取下一个任务补位
                        item = next(it, None)
                        if item is not None:
                            submit_one(item)

        # 每个分片一个 zip 句柄
        zips: dict = {}
        def get_zip_for_key(key: str):
            z = zips.get(key)
            if z is None:
                path = os.path.join(OUTPUT_DIR, f"{job_id}_{key}.zip")
                z = zipfile.ZipFile(path, mode='w', compression=zipfile.ZIP_DEFLATED)
                zips[key] = z
            return z

        seq = 0  # 全局序号，避免重名无需维护大 set
        imgs: List[Image.Image] = []
        payloads: List[Tuple[str, bytes]] = []
        bins: List[str] = []  # 对应 payloads/imgs 的时间分片 key
        for nm, dt_bytes, ts in gen_downloads():
            with JOBS_LOCK:
                if JOBS[job_id]['cancel'].is_set():
                    break
            try:
                im = Image.open(io.BytesIO(dt_bytes)).convert('RGB')
            except Exception:
                with JOBS_LOCK:
                    JOBS[job_id]['failed'] += 1
                continue
            imgs.append(im)
            payloads.append((nm, dt_bytes))
            bins.append(time_bin_key(ts))
            if len(imgs) >= batch_size:
                keeps = _predict_batch(imgs, model, conf_thresh, allowed_classes, imgsz)
                for idx, ((fn, by), k) in enumerate(zip(payloads, keeps)):
                    with JOBS_LOCK:
                        JOBS[job_id]['processed'] += 1
                    if k:
                        seq += 1
                        out = f"{seq:07d}_{fn}"
                        key = bins[idx]
                        zf = get_zip_for_key(key)
                        zf.writestr(out, by)
                        with JOBS_LOCK:
                            JOBS[job_id]['kept'] += 1
                # 释放 PIL 内存
                for im in imgs:
                    try:
                        im.close()
                    except Exception:
                        pass
                imgs.clear()
                payloads.clear()
                bins.clear()
                with JOBS_LOCK:
                    if JOBS[job_id]['cancel'].is_set():
                        break
        if imgs:
            keeps = _predict_batch(imgs, model, conf_thresh, allowed_classes, imgsz)
            for idx, ((fn, by), k) in enumerate(zip(payloads, keeps)):
                with JOBS_LOCK:
                    JOBS[job_id]['processed'] += 1
                if k:
                    seq += 1
                    out = f"{seq:07d}_{fn}"
                    key = bins[idx]
                    zf = get_zip_for_key(key)
                    zf.writestr(out, by)
                    with JOBS_LOCK:
                        JOBS[job_id]['kept'] += 1
            for im in imgs:
                try:
                    im.close()
                except Exception:
                    pass
            imgs.clear(); payloads.clear(); bins.clear()

        # 写入 summary，并关闭各分片 zip
        with JOBS_LOCK:
            jb = JOBS[job_id]
            jb['end_ts'] = int(time.time())
            if jb['cancel'].is_set() and jb['status'] == 'running':
                jb['status'] = 'canceled'
                jb['message'] = '任务已取消'
            summary = _summarize(jb)
            jb['summary_text'] = summary

        zip_parts = []
        for key, z in list(zips.items()):
            try:
                z.writestr('summary.txt', summary)
            except Exception:
                pass
            path = z.filename
            try:
                z.close()
            except Exception:
                pass
            zip_parts.append(path)

        with JOBS_LOCK:
            jb = JOBS[job_id]
            jb['zip_parts'] = [
                {'path': p, 'name': os.path.basename(p)} for p in zip_parts
            ]
            # 如果仅一个分片，保留兼容字段 zip_path
            if len(zip_parts) == 1:
                jb['zip_path'] = zip_parts[0]
            if jb['status'] == 'running':
                jb['status'] = 'done'
    except Exception as e:
        logger.exception('Job failed: %s', e)
        with JOBS_LOCK:
            jb = JOBS.get(job_id)
            if jb:
                jb['status'] = 'error'
                jb['message'] = str(e)
                jb['end_ts'] = int(time.time())


# ---------------------- 工具函数 ----------------------
def ensure_hours_list(raw_list) -> List[str]:
    hours: List[str] = []
    if not raw_list:
        return hours
    for h in raw_list if isinstance(raw_list, list) else [raw_list]:
        try:
            i = int(h)
            if 0 <= i <= 23:
                hours.append(f"{i:02d}")
        except Exception:
            pass
    return hours


def default_time_range():
    end = datetime.now()
    start = end.replace(minute=0, second=0, microsecond=0)
    fmt = '%Y-%m-%d %H:%M:%S'
    return start.strftime(fmt), end.strftime(fmt)


def to_datetime_local_str(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%dT%H:%M:%S')


def parse_and_normalize_dt(s: str) -> str:
    if not s:
        raise ValueError('时间为空')
    s = s.strip()
    fmts = [
        '%Y/%m/%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'
    ]
    dt = None
    for f in fmts:
        try:
            dt = datetime.strptime(s, f)
            break
        except Exception:
            pass
    if dt is None:
        raise ValueError(f'无法解析时间: {s}')
    return dt.strftime('%Y-%m-%d %H:%M:%S')


# ---------------------- 路由 ----------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        return redirect(url_for('index'))
    kssj, jssj = default_time_range()
    try:
        kssj_dt = datetime.strptime(kssj, '%Y-%m-%d %H:%M:%S')
        jssj_dt = datetime.strptime(jssj, '%Y-%m-%d %H:%M:%S')
    except Exception:
        now = datetime.now()
        kssj_dt = now
        jssj_dt = now
    return render_template('index.html',
                           kssj=kssj, jssj=jssj,
                           kssj_local=to_datetime_local_str(kssj_dt),
                           jssj_local=to_datetime_local_str(jssj_dt),
                           conf_default=CONF_THRESH,
                           batch_default=BATCH_SIZE,
                           imgsz_default=IMGSZ)


@app.route('/start', methods=['GET', 'POST', 'OPTIONS'])
def start_job():
    if request.method == 'OPTIONS':
        return ('', 204)
    # 兼容 GET/POST 两种提交方式
    form = request.form if request.method == 'POST' else request.args
    kssj_in = (form.get('kssj', '') or '').strip()
    jssj_in = (form.get('jssj', '') or '').strip()
    hours_raw = request.form.getlist('hours') if request.method == 'POST' else request.args.getlist('hours')
    hours = ensure_hours_list(hours_raw)

    conf_in = (form.get('conf', '') or '').strip()
    batch_in = (form.get('batch_size', '') or '').strip()
    imgsz_in = (form.get('imgsz', '') or '').strip()
    classes_raw = (form.get('classes', '') or '').strip()

    try:
        kssj = parse_and_normalize_dt(kssj_in)
        jssj = parse_and_normalize_dt(jssj_in)
    except Exception:
        kssj = kssj_in
        jssj = jssj_in
    try:
        url_and_times = fetch_image_urls(kssj, jssj, hours)
    except Exception as e:
        return jsonify({'ok': False, 'error': f'数据库查询失败: {e}'}), 500
    if not url_and_times:
        return jsonify({'ok': False, 'error': '未查询到图片 URL'}), 400

    conf_val = CONF_THRESH
    try:
        if conf_in:
            conf_val = max(0.0, min(1.0, float(conf_in)))
    except Exception:
        pass
    batch_val = BATCH_SIZE
    try:
        if batch_in:
            batch_val = max(1, int(batch_in))
    except Exception:
        pass
    imgsz_val = IMGSZ
    try:
        if imgsz_in:
            imgsz_val = max(64, int(imgsz_in))
    except Exception:
        pass

    with JOBS_LOCK:
        job = _new_job_record(total=len(url_and_times))
        # 记录任务所有者IP
        job['owner_ip'] = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or ''
        # 排他策略：同一IP的运行中任务统一置取消标志
        for j in JOBS.values():
            if j.get('status') == 'running' and j.get('owner_ip') == job['owner_ip']:
                j['cancel'].set()
        JOBS[job['id']] = job
        job_id = job['id']
    t = threading.Thread(target=_run_job, args=(job_id, url_and_times, conf_val, batch_val, imgsz_val, classes_raw), daemon=True)
    t.start()
    return jsonify({'ok': True, 'job_id': job_id, 'total': len(url_and_times)})


@app.get('/progress/<job_id>')
def get_progress(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({'ok': False, 'error': 'job not found'}), 404
        data = {k: job.get(k) for k in ('id','status','message','total','processed','kept','notfound','failed','downloaded','start_ts','end_ts','owner_ip')}
        parts = job.get('zip_parts') or []
        data['zip_parts_count'] = len(parts)
    return jsonify({'ok': True, 'job': data})


@app.post('/cancel/<job_id>')
def cancel_job(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({'ok': False, 'error': 'job not found'}), 404
        job['cancel'].set()
    return jsonify({'ok': True})


@app.get('/jobs')
def list_jobs():
    with JOBS_LOCK:
        running = [
            {k: j.get(k) for k in ('id','owner_ip','start_ts','total','processed','status')}
            for j in JOBS.values() if j.get('status') == 'running'
        ]
    return jsonify({'ok': True, 'running_count': len(running), 'running': running})


@app.get('/download/<job_id>')
def download_zip(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            flash('任务不存在')
            return redirect(url_for('index'))
        if job['status'] != 'done':
            flash('任务未完成或无可下载内容')
            return redirect(url_for('index'))
        parts = job.get('zip_parts') or []
        zip_path = job.get('zip_path')
    ts = (JOBS.get(job_id) or {}).get('end_ts') or int(time.time())
    if zip_path:
        fname = f"{ts}.zip"
        return send_file(zip_path, mimetype='application/zip', as_attachment=True, download_name=fname)
    # 多分片：返回一个简单 HTML 列表供用户逐个下载
    links = []
    for p in parts:
        name = p.get('name')
        links.append(f"<li><a href='{url_for('download_zip_part', job_id=job_id, part=name)}'>{name}</a></li>")
    html = """
    <html><head><meta charset='utf-8'><title>下载分片</title></head>
    <body><h3>检测结果较多，按日期自动切分为多个 ZIP：</h3>
    <ul>{items}</ul>
    </body></html>
    """.replace('{items}', '\n'.join(links))
    return html


@app.get('/download/<job_id>/<part>')
def download_zip_part(job_id, part):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job or job.get('status') != 'done':
            return 'job not found or not ready', 404
        parts = {p['name']: p['path'] for p in (job.get('zip_parts') or [])}
        path = parts.get(part)
    if not path or not os.path.isfile(path):
        return 'file not found', 404
    return send_file(path, mimetype='application/zip', as_attachment=True, download_name=part)


@app.get('/summary/<job_id>')
def download_summary(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return 'job not found', 404
        text = job.get('summary_text') or _summarize(job)
    return send_file(io.BytesIO(text.encode('utf-8')), mimetype='text/plain', as_attachment=True, download_name='summary.txt')


def main():
    if not os.path.isdir(INSTANT_CLIENT_DIR):
        logger.warning('instantclient 目录不存在: %s', INSTANT_CLIENT_DIR)
    try:
        get_model()
        logger.info('YOLO 模型已加载')
    except Exception as e:
        logger.warning('模型预加载失败: %s', e)
    app.run(host='0.0.0.0', port=5001, debug=False)


if __name__ == '__main__':
    main()
