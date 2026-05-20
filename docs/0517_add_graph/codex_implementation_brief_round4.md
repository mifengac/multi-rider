# Codex 第四轮任务书 — 部署与文档完善

> 前三轮已交付功能完整的系统（3 commit, 99 tests）。本轮补充**部署脚本、文档、API 参考**，使系统可真实上线运维。
> 目标：一份可部署的交付物，包含数据库初始化、配置说明、接口文档。

## 全局约束（沿用）

- 禁止新增第三方依赖；不修改已有业务代码。
- 数据库脚本：KingBase/PostgreSQL 兼容 SQL；分版本（v1.0_init, v1.1_indexes, v1.2_sample_data），支持幂等重跑。
- 文档：Markdown，面向维护人员与集成方。
- 不 git commit（由 Claude 统一提交）。

---

## U1. 数据库初始化脚本

新建目录 `scripts/sql/` 与 migration 脚本：

### U1a. `scripts/sql/v1_0_init_tables.sql`

创建新增表（KingBase/PostgreSQL 兼容）：

```sql
-- wcnr_alert 预警表
CREATE TABLE IF NOT EXISTS "jcgkzx_monitor"."wcnr_alert" (
  id SERIAL PRIMARY KEY,
  zjhm VARCHAR(18),
  xm VARCHAR(50),
  alert_type VARCHAR(50),
  alert_level VARCHAR(20),
  alert_content TEXT,
  location VARCHAR(200),
  trigger_time TIMESTAMP,
  is_read BOOLEAN DEFAULT FALSE,
  handle_status VARCHAR(50) DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(zjhm, alert_type, location, trigger_time)
);

-- wcnr_score_history 评分历史（用于同比计算）
CREATE TABLE IF NOT EXISTS "jcgkzx_monitor"."wcnr_score_history" (
  id SERIAL PRIMARY KEY,
  zjhm VARCHAR(18),
  total_score INT,
  risk_level VARCHAR(20),
  month_date DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(zjhm, month_date)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_wcnr_alert_trigger_time ON "jcgkzx_monitor"."wcnr_alert"(trigger_time DESC);
CREATE INDEX IF NOT EXISTS idx_wcnr_alert_zjhm ON "jcgkzx_monitor"."wcnr_alert"(zjhm);
CREATE INDEX IF NOT EXISTS idx_wcnr_score_history_month ON "jcgkzx_monitor"."wcnr_score_history"(month_date DESC);
```

U1b. `scripts/sql/v1_1_add_sample_data.sql`

提供 sample 预警记录（用于开发/演示）：

```sql
INSERT INTO "jcgkzx_monitor"."wcnr_alert" (zjhm, xm, alert_type, alert_level, alert_content, location, trigger_time)
VALUES 
  ('441901200812045018', '张某', 'high_risk_face_hit', 'critical', '高风险人员在XX路口被抓拍', 'XX路与XX路交叉口', NOW() - INTERVAL '30 minutes'),
  ('441901200812045019', '李某', 'night_aggregation', 'warning', '夜间聚集预警：XX网吧 3人聚集', 'XX网吧', NOW() - INTERVAL '15 minutes')
ON CONFLICT DO NOTHING;
```

### U1c. 迁移执行器脚本 `scripts/run_migrations.py`

```python
#!/usr/bin/env uv run
"""Execute SQL migration scripts in order."""
import sys
from pathlib import Path
from shared.db.kingbase import execute

def run_migrations(sql_dir: str = "scripts/sql"):
    path = Path(sql_dir)
    scripts = sorted(path.glob("v*.sql"))
    for script in scripts:
        print(f"Running {script.name}...")
        sql = script.read_text(encoding='utf-8')
        try:
            execute(sql)
            print(f"  ✓ {script.name} completed")
        except Exception as e:
            print(f"  ✗ {script.name} failed: {e}", file=sys.stderr)
            return False
    return True

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
```

---

## U2. 环境配置文档与 .env.example 补充

**更新 `.env.example`**（新增行）：

```bash
# ===== KingBase 连接（业务库）=====
KINGBASE_HOST=localhost
KINGBASE_PORT=54321
KINGBASE_DB=your_db_name
KINGBASE_USER=your_user
KINGBASE_PASSWORD=your_password
KINGBASE_SCHEMA=ywdata

# ===== 聚合层配置（jcgkzx_monitor schema）=====
# 通常与 KingBase 同连接，但 schema 切换
JCGKZX_MONITOR_SCHEMA=jcgkzx_monitor

# ===== 调度器配置 =====
WCNR_SCHEDULER_ENABLED=1
WCNR_SCHEDULER_BATCH_HOUR=3       # 日批时刻(小时): 03:00
WCNR_SCHEDULER_DECAY_DOM=1        # 月衰减日期: 1号 04:00
WCNR_SCHEDULER_ALERT_SCAN_MINUTES=5  # alert 规则扫描间隔: 5min
WCNR_SCHEDULER_INCREMENTAL_MINUTES=10  # 增量评分扫描: 10min

# ===== 部署环境 =====
FLASK_ENV=production              # development / production
DEBUG=0
```

**新建 `docs/DEPLOYMENT.md`**（部署指南）：

```markdown
# 部署指南

## 前置要求

- Python 3.12 + uv 包管理器
- KingBase V8（或 PostgreSQL 兼容）
- 4GB+ 内存，2 核 CPU

## 快速启动

### 1. 环境配置

cp .env.example .env
# 编辑 .env，填入 KingBase 连接信息

### 2. 数据库初始化

uv run python scripts/run_migrations.py

### 3. 启动服务

python app.py

访问: http://localhost:5000/dashboard

## 配置说明

| 变量 | 含义 | 默认 | 说明 |
|------|------|------|------|
| KINGBASE_HOST | 主机 | localhost | |
| KINGBASE_DB | 数据库名 | - | 必填 |
| WCNR_SCHEDULER_ENABLED | 启用调度器 | 1 | 测试时设 0 |
| WCNR_SCHEDULER_BATCH_HOUR | 日批时刻 | 3 | 凌晨 3 点 |

## 离线安装（内网）

```bash
pip install --no-index --find-links ./wheels -r requirements.txt
```

## 监控与维护

### 日志

调度器日志输出到 stderr；Flask 日志配置见 `shared/logging.py`。

### 健康检查

```bash
curl http://localhost:5000/api/health
# 返回: {"status": "ok", "scheduler": "running", "db": "connected"}
```

### 性能优化

- 评分表缓存: `REDIS_URL=redis://...` 启用（可选）
- 数据库连接池: `KINGBASE_POOL_SIZE=10`
```

---

## U3. API 参考文档

新建 `docs/API.md`：

列举全部端点（按模块）：

```markdown
# API 参考手册

## 认证

所有 API 无认证（内网环保境）。

## 图谱 `/api/graph`

| 方法 | 路径 | 参数 | 返回 | 说明 |
|------|------|------|------|------|
| GET | `/person/<zjhm>` | depth=1-3, relations=, time_range= | nodes[], edges[] | 人物子图 |
| GET | `/case/<ajbh>` | depth=1-3 | nodes[], edges[] | 案件子图 |
| POST | `/expand` | {node_id, node_type, direction} | nodes[], edges[] | 节点扩展 |
| GET | `/search` | keyword=, type= | [{id,type,label}] | 节点搜索 |
| GET | `/paths` | from=, to=, max_hops=4 | {found, path, hops} | 最短路径 |

## 评分 `/api/score`

| 方法 | 路径 | 参数 | 返回 | 说明 |
|------|------|------|------|------|
| GET | `/<zjhm>` | - | {total_score, risk_level, dim_*} | 个人评分 |
| GET | `/list` | min_score=, max_score=, page=1, size=20 | {total, items} | 高风险列表 |
| GET | `/trend/<zjhm>` | months=6 | {points: [{month, score}]} | 评分趋势 |
| POST | `/recalculate` | {zjhm: all} | {status, message} | 触发重算 |
| POST | `/batch-recalculate` | - | {status, message} | 全量重算 |

## 画像 `/api/profile`

| 方法 | 路径 | 参数 | 返回 | 说明 |
|------|------|------|------|------|
| GET | `/<zjhm>` | - | {basic, score, cases, behaviors, relations, suggestions, trajectory} | 完整画像 |
| GET | `/<zjhm>/trajectory` | days=30 | {recent, hotspots, time_pattern, last_seen} | 轨迹详情 |
| GET | `/<zjhm>/timeline` | - | [{time, type, title, detail}] | 事件时间轴 |
| GET | `/<zjhm>/photo` | - | {zp, zp_source} | 人口照片 |

## 面板 `/api/dashboard`

| 方法 | 路径 | 参数 | 返回 | 说明 |
|------|------|------|------|------|
| GET | `/summary` | - | {total_persons, high_risk_count, month_cases, avg_score, *_prev, *_change_pct} | 核心指标 |
| GET | `/trend` | months=12, metric=cases\|persons\|score | {points: [{month, count}]} | 月度趋势 |
| GET | `/distribution` | dim=case_type\|risk_level\|area\|age\|gender\|source | {items: [{label, value}]} | 分布统计 |
| GET | `/heatmap` | days=30 | [{lng, lat, weight}] | 热力图数据 |
| GET | `/alerts` | limit=20 | {items: [{id, zjhm, xm, alert_type, trigger_time}]} | 预警列表 |
| GET | `/alerts/stream` | - | text/event-stream | SSE 实时推送 |
| POST | `/alerts/<id>/read` | - | {success} | 标记已读 |
| POST | `/alerts/<id>/handle` | {status} | {success} | 处理预警 |
| POST | `/alerts/scan` | - | {high_risk_face_hit, night_aggregation, abnormal_hotel_checkin, school_perimeter_high_risk, speeding_detected} | 手动触发规则扫描 |
| POST | `/dispatch/from-person` | {zjhm} | {ok, redirect} | 派发任务跳转 |
| GET | `/ranking` | by=area\|school, metric=case_count\|risk_count | {items} | 辖区/学校排名 |

## 错误响应

所有错误返回 JSON：

```json
{
  "error": "error_code",
  "message": "Human-readable message"
}
```

| 状态码 | 说明 |
|--------|------|
| 400 | 参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器错误（多为数据库连接） |
```

---

## U4. API 输入验证增强

在各路由加参数检查（示例）：

`modules/graph/routes.py` 的 `/person/<zjhm>` 增：

```python
from shared.validators import validate_zjhm, validate_depth, validate_relations, validate_time_range

@graph_bp.route("/person/<zjhm>", methods=["GET"])
def person_graph(zjhm):
    # 参数验证
    if not validate_zjhm(zjhm):
        return jsonify({"error": "invalid_zjhm"}), 400
    
    depth = request.args.get("depth", 1, type=int)
    if not validate_depth(depth):
        return jsonify({"error": "invalid_depth"}), 400
    
    relations = request.args.get("relations")
    if relations and not validate_relations(relations):
        return jsonify({"error": "invalid_relations"}), 400
    
    # ... 后续逻辑
```

新建 `shared/validators.py`：

```python
import re

def validate_zjhm(zjhm: str) -> bool:
    """验证 18 位身份证号或 15 位（不含校验位）"""
    if not zjhm:
        return False
    return len(zjhm) in (15, 18) and re.match(r'^\d{15,18}$', zjhm)

def validate_depth(depth: int) -> bool:
    return 1 <= depth <= 3

def validate_relations(relations: str) -> bool:
    valid = {'suspected_in', 'co_suspect', 'guardian_of', 'studies_at', 
             'appeared_at', 'checked_in', 'lives_at', 'same_school', 'same_area'}
    parts = set(relations.split(','))
    return parts.issubset(valid)

def validate_time_range(tr: str) -> bool:
    return tr in {None, '', '1m', '3m', '6m', '1y'}
```

在关键路由应用验证（graph, score, profile, dashboard 各核心路由）；错误一律返回 400。

---

## U5. 前端 UX 增强

### U5a. 统一错误处理 `static/modules/shared.js`

```javascript
// 错误弹窗替代 alert()
function showError(message, title = '错误') {
  const html = `
    <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-lg p-6 max-w-sm">
        <h3 class="text-lg font-bold text-red-600 mb-2">${title}</h3>
        <p class="text-sm text-slate-600 mb-4">${message}</p>
        <button onclick="this.closest('div').parentElement.remove()" 
                class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">
          关闭
        </button>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);
}

// 加载态 spinner
function showLoading(text = '加载中...') {
  const html = `
    <div id="loading-spinner" class="fixed inset-0 bg-black/30 flex items-center justify-center z-40">
      <div class="text-center">
        <div class="animate-spin w-12 h-12 border-4 border-white border-t-blue-500 rounded-full mx-auto mb-2"></div>
        <p class="text-white text-sm">${text}</p>
      </div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', html);
}

function hideLoading() {
  document.getElementById('loading-spinner')?.remove();
}
```

### U5b. 各模块应用

- `dashboard.js`: API fetch 失败 → `showError("加载数据失败，请稍后重试")`
- `graph.js`: ditto
- `profile.js`: ditto
- 关键操作（派发、扫描）前显示 `showLoading()`

### U5c. 分页/虚拟滚动（可选，alert 列表）

若 alert 超过 50 条，分页显示（简单实现）：

```javascript
const ITEMS_PER_PAGE = 20;
let currentPage = 1;

function paginate(items) {
  const start = (currentPage - 1) * ITEMS_PER_PAGE;
  const end = start + ITEMS_PER_PAGE;
  return items.slice(start, end);
}
```

---

## U6. Dockerfile（如缺失）

新建 `Dockerfile`（多阶段构建，优化大小）：

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV WCNR_SCHEDULER_ENABLED=1

EXPOSE 5000

CMD ["python", "app.py"]
```

更新 `docker-compose.yml` 支持新表初始化：

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      KINGBASE_HOST: kingbase
      KINGBASE_USER: postgres
      KINGBASE_PASSWORD: postgres
    depends_on:
      - kingbase
    command: bash -c "uv run python scripts/run_migrations.py && python app.py"
  
  kingbase:
    image: kingbase/kingbase8-container:latest  # 或指定具体版本
    environment:
      KINGBASE_PASSWORD: postgres
    volumes:
      - kingbase_data:/var/lib/kingbase

volumes:
  kingbase_data:
```

---

## U7. 健康检查端点

`modules/diagnostics/routes.py` 或新建 `shared/health.py`：

```python
@app.route("/api/health", methods=["GET"])
def health_check():
    from shared.db.kingbase import query_one
    from shared.scheduler import is_scheduler_running
    
    db_ok = False
    try:
        query_one("SELECT 1")
        db_ok = True
    except:
        pass
    
    return jsonify({
        "status": "ok" if db_ok else "degraded",
        "db": "connected" if db_ok else "disconnected",
        "scheduler": "running" if is_scheduler_running() else "stopped",
        "timestamp": datetime.utcnow().isoformat()
    })
```

---

## 验收

- 新增脚本：`scripts/sql/v*.sql`, `scripts/run_migrations.py`
- 新增文档：`docs/DEPLOYMENT.md`, `docs/API.md`（补充 `.env.example`）
- 新增验证器：`shared/validators.py`
- 新增 UX：`static/modules/shared.js`（error/loading）
- 可选：`Dockerfile` 更新 / 健康检查端点
- 测试：99+ passed（验证 validators 调用）；`docker-compose up` 可成功启动（如提供 KingBase 镜像）
- 文档：README.md 补充新模块说明；API.md 列全部端点

不要 git commit。完成后逐项报告改动文件清单与验收结果。
