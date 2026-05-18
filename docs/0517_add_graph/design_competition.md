# 未成年人智能管控中枢 - 比赛版实施方案

> 比赛：省数字侦查比赛（刑侦方向）  
> 截止：2026-05-30  
> 主题：打击预防未成年人侵财  
> 原则：能跑、能演示、别翻车  

---

## 一、实施范围与优先级

| 优先级 | 模块 | 工作量 | 交付标准 |
|--------|------|--------|----------|
| P0 | 数据层（建表+ETL） | 1天 | wcnr_* 表就绪，数据可查 |
| P0 | 风险评分 | 1.5天 | 全量评分完成，API可调用 |
| P0 | 个人画像 | 2天 | 单人画像页面可展示 |
| P1 | 统计面板 | 2天 | 大屏可演示 |
| P1 | 关系图谱 | 2.5天 | 1-2层关系可视化 |
| P2 | 串联演示流程 | 1天 | 面板→画像→图谱→下发完整链路 |

**总计约10天，需在13天内完成，含调试缓冲。**

**实施顺序：数据层 → 评分 → 画像 → 面板 → 图谱 → 串联**

---

## 二、数据层设计

### 2.1 Schema与命名规范

- **Schema**: `jcgkzx_monitor`
- **前缀**: `wcnr_`
- **SQL规范**: 遵循 Kingbase V8 兼容性
  - 用 `IS NOT NULL` 代替 `<> ''`
  - 表名带schema前缀: `"jcgkzx_monitor"."wcnr_xxx"`
  - 区域分组走字典表 `stdata.b_dic_zzjgdm`

### 2.2 管控对象池（核心基准表）

```sql
CREATE TABLE "jcgkzx_monitor"."wcnr_target_pool" (
    zjhm          VARCHAR(18) PRIMARY KEY,
    xm            VARCHAR(50),
    xb            VARCHAR(4),
    csrq          VARCHAR(20),
    source_type   VARCHAR(30),   -- dropout/truant/lost/suspect/bczj/correction
    risk_score    INTEGER DEFAULT 0,
    risk_level    VARCHAR(10),   -- extreme/high/medium/low/normal
    ssfj          VARCHAR(50),   -- 所属分局
    ssfjdm        VARCHAR(12),   -- 所属分局代码
    sspcs         VARCHAR(50),   -- 所属派出所
    sspcsdm       VARCHAR(12),   -- 所属派出所代码
    create_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE "jcgkzx_monitor"."wcnr_target_pool" IS '未成年人管控对象池';
```

**数据来源汇总（去重合并）：**

| 来源表 | source_type | 数据量 |
|--------|-------------|--------|
| `ywdata.b_per_qscxwcnr` | dropout | 1,921 |
| `ywdata.b_per_qskjwcnr` | truant | 18,812 |
| `ywdata.b_per_qslswcnr` | lost | 36,659 |
| `ywdata.zq_zfba_wcnr_xyr` | suspect | 4,905 |
| `ywdata.b_per_qswcnrbczj` | bczj | 300 |
| `ywdata.b_per_qsyzjszawcnr` | correction | 302 |
| **去重后预估** | - | **~40,000-50,000** |

### 2.3 抽取表定义

#### (1) 人脸轨迹表

```sql
CREATE TABLE "jcgkzx_monitor"."wcnr_ryrl_gj" (
    id            BIGSERIAL PRIMARY KEY,
    zjhm          VARCHAR(18),        -- 身份证号(关联target_pool)
    xm            VARCHAR(50),
    device_id     VARCHAR(50),        -- 设备ID
    device_name   VARCHAR(200),       -- 设备名称/位置
    shot_time     TIMESTAMP,          -- 抓拍时间
    face_image    TEXT,               -- 人脸图片路径/base64
    jd            NUMERIC(12,8),      -- 经度
    wd            NUMERIC(12,8),      -- 纬度
    ssfj          VARCHAR(50),
    sspcs         VARCHAR(50)
);

CREATE INDEX idx_wcnr_ryrl_zjhm ON "jcgkzx_monitor"."wcnr_ryrl_gj"(zjhm);
CREATE INDEX idx_wcnr_ryrl_shot_time ON "jcgkzx_monitor"."wcnr_ryrl_gj"(shot_time);
CREATE INDEX idx_wcnr_ryrl_device ON "jcgkzx_monitor"."wcnr_ryrl_gj"(device_id);

COMMENT ON TABLE "jcgkzx_monitor"."wcnr_ryrl_gj" IS '未成年人人脸轨迹（从t_spy_ryrlgj_xx抽取，libname=全市未成年人）';
```

**抽取SQL：**
```sql
INSERT INTO "jcgkzx_monitor"."wcnr_ryrl_gj"
    (zjhm, xm, device_id, device_name, shot_time, face_image, jd, wd, ssfj, sspcs)
SELECT
    s.id_number, s.name, s.device_id, s.device_name, s.shot_time,
    s.face_image, s.jd, s.wd, s.ssfj, s.sspcs
FROM "ywdata"."t_spy_ryrlgj_xx" s
WHERE s.libname = '全市未成��人'
  AND s.shot_time >= '2026-01-01'::TIMESTAMP;
```

#### (2) 旅馆入住表

```sql
CREATE TABLE "jcgkzx_monitor"."wcnr_ly_checkin" (
    id            BIGSERIAL PRIMARY KEY,
    zjhm          VARCHAR(18),
    xm            VARCHAR(50),
    xb            VARCHAR(4),
    nl            INTEGER,           -- 年龄
    lgmc          VARCHAR(200),      -- 旅馆名称
    lgdz          VARCHAR(300),      -- 旅馆地址
    rzsj          TIMESTAMP,         -- 入住时间
    lksj          TIMESTAMP,         -- 离开时间
    tfrxm         VARCHAR(50),       -- 同房人姓名
    tfrzjhm       VARCHAR(18),       -- 同房人证件号
    ssfj          VARCHAR(50),
    sspcs         VARCHAR(50)
);

CREATE INDEX idx_wcnr_ly_zjhm ON "jcgkzx_monitor"."wcnr_ly_checkin"(zjhm);
CREATE INDEX idx_wcnr_ly_rzsj ON "jcgkzx_monitor"."wcnr_ly_checkin"(rzsj);

COMMENT ON TABLE "jcgkzx_monitor"."wcnr_ly_checkin" IS '未成年人旅馆入住（从t_ly_checkin_gn_merge抽取）';
```

**抽取SQL：**
```sql
INSERT INTO "jcgkzx_monitor"."wcnr_ly_checkin"
    (zjhm, xm, xb, nl, lgmc, lgdz, rzsj, lksj, tfrxm, tfrzjhm, ssfj, sspcs)
SELECT
    l.zjhm, l.xm, l.xb, l.nl, l.lgmc, l.lgdz, l.rzsj, l.lksj,
    l.tfrxm, l.tfrzjhm, l.ssfj, l.sspcs
FROM "ywdata"."t_ly_checkin_gn_merge" l
WHERE l.zjhm IN (SELECT zjhm FROM "jcgkzx_monitor"."wcnr_target_pool")
  AND l.rzsj >= '2025-01-01'::TIMESTAMP;
```

#### (3) 人口照片表

```sql
CREATE TABLE "jcgkzx_monitor"."wcnr_rk_zp" (
    zjhm          VARCHAR(18) PRIMARY KEY,
    xm            VARCHAR(50),
    zp            TEXT,              -- 照片(base64或路径)
    zp_source     VARCHAR(20),      -- 来源: dsfb/czrk
    update_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE "jcgkzx_monitor"."wcnr_rk_zp" IS '未成年人照片（从t_dsfb_rk_zpxx/t_ap_czrk_zp抽取）';
```

**抽取SQL：**
```sql
INSERT INTO "jcgkzx_monitor"."wcnr_rk_zp" (zjhm, xm, zp, zp_source)
SELECT r.zjhm, r.xm, r.zp, 'dsfb'
FROM "ywdata"."t_dsfb_rk_zpxx" r
WHERE r.zjhm IN (SELECT zjhm FROM "jcgkzx_monitor"."wcnr_target_pool")
ON CONFLICT (zjhm) DO NOTHING;
```

#### (4) 常住人口基本信息

```sql
CREATE TABLE "jcgkzx_monitor"."wcnr_czrk" (
    zjhm          VARCHAR(18) PRIMARY KEY,
    xm            VARCHAR(50),
    xb            VARCHAR(4),
    mz            VARCHAR(20),
    csrq          VARCHAR(20),
    hjdz          VARCHAR(300),     -- 户籍地址
    xzdxz         VARCHAR(300),     -- 现住地址
    whcd          VARCHAR(20),      -- 文化程度
    fqxm          VARCHAR(50),      -- 父亲姓名
    fqzjhm        VARCHAR(18),
    mqxm          VARCHAR(50),      -- 母亲姓名
    mqzjhm        VARCHAR(18),
    lxdh          VARCHAR(30)
);

COMMENT ON TABLE "jcgkzx_monitor"."wcnr_czrk" IS '未成年人常住人口信息（从t_ap_czrk_jbxx抽取）';
```

#### (5) 风险评分结果表

```sql
CREATE TABLE "jcgkzx_monitor"."wcnr_score" (
    zjhm              VARCHAR(18) PRIMARY KEY,
    total_score       INTEGER DEFAULT 0,       -- 总分(0-100)
    risk_level        VARCHAR(10),             -- extreme/high/medium/low/normal
    dim_case          INTEGER DEFAULT 0,       -- 案件维度(0-30)
    dim_behavior      INTEGER DEFAULT 0,       -- 行为维度(0-25)
    dim_family        INTEGER DEFAULT 0,       -- 家庭维度(0-20)
    dim_education     INTEGER DEFAULT 0,       -- 教育维度(0-15)
    dim_social        INTEGER DEFAULT 0,       -- 社交维度(0-10)
    calc_time         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    detail_json       TEXT                     -- 各维度计算明细JSON
);

COMMENT ON TABLE "jcgkzx_monitor"."wcnr_score" IS '未成年人风险评分结果';
```

#### (6) 评分历史表

```sql
CREATE TABLE "jcgkzx_monitor"."wcnr_score_history" (
    id            BIGSERIAL PRIMARY KEY,
    zjhm          VARCHAR(18),
    total_score   INTEGER,
    risk_level    VARCHAR(10),
    calc_time     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_wcnr_score_hist_zjhm ON "jcgkzx_monitor"."wcnr_score_history"(zjhm);

COMMENT ON TABLE "jcgkzx_monitor"."wcnr_score_history" IS '未成年人风险评分历史（趋势分析用）';
```

#### (7) 预警记录表

```sql
CREATE TABLE "jcgkzx_monitor"."wcnr_alert" (
    id            BIGSERIAL PRIMARY KEY,
    zjhm          VARCHAR(18),
    xm            VARCHAR(50),
    alert_type    VARCHAR(30),       -- face_appear/night_gather/hotel/bczj/school_nearby
    alert_level   VARCHAR(10),       -- critical/warning/info
    alert_content TEXT,              -- 预警描述
    location      VARCHAR(300),      -- 触发地点
    jd            NUMERIC(12,8),
    wd            NUMERIC(12,8),
    trigger_time  TIMESTAMP,         -- 触发时间
    is_read       BOOLEAN DEFAULT FALSE,
    handle_status VARCHAR(10) DEFAULT 'pending'  -- pending/handled/dismissed
);

CREATE INDEX idx_wcnr_alert_time ON "jcgkzx_monitor"."wcnr_alert"(trigger_time DESC);
CREATE INDEX idx_wcnr_alert_zjhm ON "jcgkzx_monitor"."wcnr_alert"(zjhm);

COMMENT ON TABLE "jcgkzx_monitor"."wcnr_alert" IS '未成年人预警记录';
```

### 2.4 ETL执行顺序

```
1. 创建所有表结构
2. 填充 wcnr_target_pool（多来源去重合并）
3. 填充 wcnr_czrk（人口基本信息）
4. 填充 wcnr_rk_zp（照片）
5. 填充 wcnr_ly_checkin（旅馆入住）
6. 填充 wcnr_ryrl_gj（人脸轨迹，最耗时）
7. 运行评分引擎 → 填充 wcnr_score
```

---

## 三、风险评分模块

### 3.1 模块结构

```
modules/score/
├── __init__.py
├── routes.py                  # API路由
└── services/
    ��── __init__.py
    ├── score_engine.py        # 评分引擎主逻辑
    ├── dim_case.py            # 案件维度(30分)
    ├── dim_behavior.py        # 行为维度(25分)
    ├─�� dim_family.py          # 家庭维度(20分)
    ├── dim_education.py       # 教育维度(15分)
    ├── dim_social.py          # 社交维度(10分)
    └── score_store.py         # 存储/更新评分结果
```

### 3.2 评分规则

#### 案件维度（满分30）

| 条件 | 分值 |
|------|------|
| 涉案1起 | +8 |
| 涉案2起 | +15 |
| 涉案3起+ | +22 |
| 案由:抢劫/抢夺/故意伤害 | 每起+4 |
| 案由:盗窃/诈骗 | 每起+3 |
| 案由:寻衅滋事/聚众斗殴 | 每起+2 |
| 超过1年的案件 | 权重减半 |

**数据源SQL：**
```sql
SELECT a.ajxx_ajbh, a.ajxx_ay, a.ajxx_fasj
FROM "ywdata"."zq_zfba_wcnr_ajxx" a
JOIN "ywdata"."zq_zfba_wcnr_xyr" x
  ON x.ajxx_join_ajxx_ajbh = a.ajxx_ajbh
WHERE x.xyrxx_sfzh = :zjhm;

-- 补充飙车案件
SELECT ajbh, ay, wfsj
FROM "ywdata"."b_evt_jjzdbczjajxx"
WHERE dsrsfzmhm = :zjhm;
```

#### 行为维度（满分25）

| 行为类型 | 单次分值 |
|----------|----------|
| 飙车 | 5 |
| 盗窃 | 5 |
| 斗殴 | 4 |
| 寻衅滋事 | 4 |
| 损毁财物 | 3 |
| 翘课聚集 | 2 |

时间衰减：近3月 x1.5，3-6月 x1.0，6月以上 x0.5

**数据源SQL：**
```sql
SELECT wf_sj, wfxw_cn, blxwlx_cn
FROM "ywdata"."t_wcnrxwjl_xx"
WHERE sfzhm = :zjhm;

SELECT wfnr, wfrq
FROM "ywdata"."b_per_qswcnrbczj"
WHERE sfzhm = :zjhm;
```

#### 家庭维度（满分20）

| 条件 | 分值 |
|------|------|
| 父母双方外出务工 | +8 |
| 单亲外出务工 | +5 |
| 困难家庭(低保/边缘) | +5 |
| 监护人缺失/无监护能力 | +10 |
| 儿童类别:留守/困境/孤儿 | +4 |

**数据源SQL：**
```sql
SELECT fxdj, jtqk, jhr1xm, jhr1lxdh, etlb, knjtlx, fmsftswc
FROM "ywdata"."b_per_qskjwcnr"
WHERE zjhm = :zjhm;
```

#### 教育维度（满分15）

| 状态 | 分值 |
|------|------|
| 辍学 | 15 |
| 流失(去向不明) | 13 |
| 旷课(频繁) | 10 |
| 旷课(偶尔) | 6 |
| 正常在校 | 0 |

**数据源SQL：**
```sql
-- 辍学
SELECT 1 FROM "ywdata"."b_per_qscxwcnr" WHERE zjhm = :zjhm;
-- 旷课
SELECT jxqk FROM "ywdata"."b_per_qskjwcnr" WHERE zjhm = :zjhm;
-- 流失
SELECT 1 FROM "ywdata"."b_per_qslswcnr" WHERE zjhm = :zjhm;
```

#### 社交维度（满分10）

| 条件 | 分值 |
|------|------|
| 每个高风险关联人(score>=60) | +3（最高7） |
| 3人+共同犯罪 | +3 |

**计算逻辑：** 依赖图谱模块的共犯关系数据。比赛版简化为：查同案件编号下其他嫌疑人的评分。

### 3.3 风险等级映射

| 分数 | 等级 | 标识 | 颜色 |
|------|------|------|------|
| 80-100 | 极高风险 | extreme | #DC2626 红 |
| 60-79 | 高风险 | high | #EA580C 橙 |
| 40-59 | 中风险 | medium | #CA8A04 黄 |
| 20-39 | 低风险 | low | #2563EB 蓝 |
| 0-19 | 基本正常 | normal | #16A34A 绿 |

### 3.4 API

```
GET  /api/score/{zjhm}
     → { zjhm, xm, total_score, risk_level, dimensions: {...}, calc_time }

GET  /api/score/list?min_score=60&area_code=xxx&page=1&size=20&sort=desc
     → { total, items: [...] }

GET  /api/score/trend/{zjhm}?months=6
     → { points: [{month, score}, ...] }

POST /api/score/recalculate
     body: { zjhm: "all" | "specific_zjhm" }
     → { status: "started", count: N }
```

---

## 四、个人画像模块

### 4.1 模块结构

```
modules/profile/
├─��� __init__.py
├── routes.py
└── services/
    ├��─ __init__.py
    ├── profile_assembler.py     # 数据聚合
    ├── trajectory_service.py    # 轨迹分析
    └── suggestion_engine.py     # 管控建议(规则)
```

### 4.2 画像页面结构

```
┌─────────────────────────────────────────────────────────────┐
│ [照片] 张某某(男,16岁)    风险评分:72  ████████░░ [高风险]  │
│        身份证:440XXXXXXX  户籍:XX市XX区                      │
│        学校:XX中学(已辍学) 监护人:张某父(139XXXX)            │
├─────────────────────────────────────────────────────────────┤
│ 【基本信息】民族|文化|家庭|经济|监护状态                     │
├─────────────────────────────────────────────────────────────┤
│ 【涉案记录】按时间倒序，显示案由+承办单位+状态               │
├─────────────────────────────────────────────────────────────┤
│ 【行为记录】违法行为+不良行为，按时间倒序                    │
├──────────────────��──────────────────────────────────────────┤
│ 【轨迹分析】近期出现地点列表 + 高频地点Top5 + 活动时段       │
├─────────────────────────────────────────────────────────────┤
│ 【关系网络】迷你图谱(仅1层) + 关联人员列表                   │
├───────────────────��───────────────────────────────���─────────┤
│ 【评分明细】各维度分数 + 近6月趋势折线                       │
├──��──────────────────────────────────────────────────────────┤
│ 【管控建议】规则引擎生成的处置建议                           │
└──────────────────────────────────���──────────────────────────┘
```

### 4.3 数据聚合API

```
GET /api/profile/{zjhm}
```

**返回结构：**
```json
{
  "basic": { "zjhm", "xm", "xb", "nl", "mz", "whcd", "hjdz", "xzdxz", "photo_url" },
  "family": { "jhr_xm", "jhr_lxdh", "jhr_gx", "jtqk", "knjtlx", "etlb" },
  "education": { "status", "school_name", "jxqk" },
  "cases": [{ "ajbh", "ajmc", "ay", "fasj", "cbdw", "status" }],
  "behaviors": [{ "time", "type", "content", "location" }],
  "trajectory": {
    "recent": [{ "time", "location", "device_id" }],
    "hotspots": [{ "location", "count" }],
    "time_pattern": { "night_ratio", "peak_hours" }
  },
  "relations": {
    "co_suspects": [{ "zjhm", "xm", "case_count", "risk_score" }],
    "guardians": [{ "xm", "gx", "lxdh" }]
  },
  "score": { "total", "dimensions", "trend" },
  "suggestions": ["建议1", "建议2", "..."]
}
```

### 4.4 管控建议规则

```python
rules = [
    (score >= 80 and education == 'dropout',
     "建议联合教育部门劝返复学，每周走访"),
    (dim_family >= 15,
     "家庭监护缺失，建议联系民政部门介入"),
    (night_trajectory_ratio > 0.4,
     f"夜间活跃占比{ratio}%，加强{hotspot}路段夜间巡逻"),
    (co_suspect_count >= 3,
     f"存在{count}人团伙关联，注意聚集预警"),
    (hotel_no_guardian,
     "近期无监护人陪同入住旅馆，建议约谈旅馆"),
]
```

### 4.5 前端技术

- 页面: `templates/modules/profile/profile.html`
- 脚本: `static/modules/profile/profile.js`
- 迷你图谱: AntV G6 (同图谱模块共用)
- 趋势图: ECharts line chart
- 样式: Tailwind CSS

---

## 五、统计面板模块

### 5.1 模块结构

```
modules/dashboard/
├── __init__.py
├── routes.py
└── services/
    ├── __init__.py
    ├── summary_service.py       # 核心指标
    ├── trend_service.py         # 趋势
    ├── distribution_service.py  # 分布
    └── alert_service.py         # 预警
```

### 5.2 面板布局

```
┌──────────────────────────────────────────────────────────┐
│  未成年人智能管控中枢 - 态势总览              2026-05-17  │
├──────────┬──────────┬──────────┬──────────┬──────────────┤
│ 管控总人数│ 高风险   │ 本月新增 │ 本月走访  │             │
│  数字卡片 │ 数字卡片 │ 数字卡片 │ 数字卡片  │  [地图区]   │
├──────────┴──────────┴──────────┴──────────┤  热力图     │
│ [案件类型饼图]        [月度趋势折线图]     │  或辖区分布 │
├────────────────────────────────────────────┼──────────────┤
│ [风险等级环形图]      [年龄/性别分布]      │ [辖区排名]  │
├────────────────────���───────────────────────┼──────────────┤
│ [实时预警滚动列表]                         │ [时段分布]  │
└────────────────���───────────────────────────┴──────────────┘
```

### 5.3 核心指标SQL

```sql
-- 管控总人数
SELECT COUNT(*) FROM "jcgkzx_monitor"."wcnr_target_pool";

-- 高风险人数
SELECT COUNT(*) FROM "jcgkzx_monitor"."wcnr_score"
WHERE total_score >= 60;

-- 本月新增案件
SELECT COUNT(*) FROM "ywdata"."zq_zfba_wcnr_ajxx"
WHERE ajxx_fasj >= DATE_TRUNC('month', CURRENT_DATE);

-- 案件类型分布
SELECT ajxx_ay, COUNT(*) AS cnt
FROM "ywdata"."zq_zfba_wcnr_ajxx"
WHERE ajxx_fasj >= CURRENT_DATE - INTERVAL '1 year'
GROUP BY ajxx_ay
ORDER BY cnt DESC;

-- 辖区分布(分局级)
SELECT d.ssfj, COUNT(*) AS cnt
FROM "jcgkzx_monitor"."wcnr_score" s
JOIN "jcgkzx_monitor"."wcnr_target_pool" p ON p.zjhm = s.zjhm
LEFT JOIN "stdata"."b_dic_zzjgdm" d ON d.ssfjdm = p.ssfjdm
WHERE s.total_score >= 60
GROUP BY d.ssfj
ORDER BY cnt DESC;

-- 年龄分布
SELECT
    CASE
        WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, csrq::DATE)) < 14 THEN '14岁以下'
        WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, csrq::DATE)) BETWEEN 14 AND 15 THEN '14-16岁'
        ELSE '16-18岁'
    END AS age_group,
    COUNT(*) AS cnt
FROM "jcgkzx_monitor"."wcnr_target_pool"
WHERE csrq IS NOT NULL
GROUP BY age_group;

-- 月度趋势(近12月)
SELECT
    TO_CHAR(ajxx_fasj, 'YYYY-MM') AS month,
    COUNT(*) AS case_count
FROM "ywdata"."zq_zfba_wcnr_ajxx"
WHERE ajxx_fasj >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY TO_CHAR(ajxx_fasj, 'YYYY-MM')
ORDER BY month;
```

### 5.4 API

```
GET /api/dashboard/summary
    → { total_persons, high_risk_count, month_cases, month_visits }

GET /api/dashboard/trend?months=12&metric=cases|persons|score
    → { points: [{month, value}] }

GET /api/dashboard/distribution?dim=case_type|risk_level|area|age|gender
    → { items: [{label, value}] }

GET /api/dashboard/alerts?limit=20
    → { items: [{id, zjhm, xm, type, content, time, level}] }

GET /api/dashboard/ranking?by=area&metric=risk_count&limit=10
    → { items: [{name, value}] }
```

### 5.5 前端技术

- 页面: `templates/modules/dashboard/dashboard.html`
- 脚本: `static/modules/dashboard/dashboard.js`
- 图表: ECharts (饼图、折线图、环形图、柱状图)
- 地图: 离线方案用ECharts map（内网无法调高德API）
- 样式: Tailwind CSS，深色主题大屏风格

---

## 六、关系图谱模块（比赛简化版）

### 6.1 模块结构

```
modules/graph/
├── __init__.py
├── routes.py
└── services/
    ├── __init__.py
    ├── graph_builder.py       # SQL→节点/边构建
    └── path_finder.py         # NetworkX路径计算
```

### 6.2 比赛版范围（只做这些）

| 节点类型 | 数据源 |
|----------|--------|
| Person(人) | wcnr_target_pool + wcnr_czrk |
| Case(案件) | zq_zfba_wcnr_ajxx |
| School(学校) | b_per_qscxwcnr.yxx / b_yfszxxxsxx |
| Guardian(监护人) | b_per_qskjwcnr.jhr1xm |

| 边类型 | 逻辑 |
|--------|------|
| SUSPECTED_IN | 人→案件（嫌疑人关联） |
| CO_SUSPECT | 人→人（同案件号下的不同嫌疑人） |
| GUARDIAN_OF | 监护人→人 |
| STUDIES_AT | 人→学校 |

### 6.3 图构建SQL

```sql
-- 获取某人的1层子图
-- 1. 涉案关系
SELECT x.xyrxx_sfzh AS person_zjhm, a.ajxx_ajbh, a.ajxx_ajmc, a.ajxx_ay, a.ajxx_fasj
FROM "ywdata"."zq_zfba_wcnr_xyr" x
JOIN "ywdata"."zq_zfba_wcnr_ajxx" a ON a.ajxx_ajbh = x.ajxx_join_ajxx_ajbh
WHERE x.xyrxx_sfzh = :zjhm;

-- 2. 共犯（同案件的其他嫌疑人）
SELECT x2.xyrxx_sfzh, x2.xyrxx_xm
FROM "ywdata"."zq_zfba_wcnr_xyr" x1
JOIN "ywdata"."zq_zfba_wcnr_xyr" x2
  ON x2.ajxx_join_ajxx_ajbh = x1.ajxx_join_ajxx_ajbh
  AND x2.xyrxx_sfzh <> x1.xyrxx_sfzh
WHERE x1.xyrxx_sfzh = :zjhm;

-- 3. 监护关系
SELECT jhr1xm, jhr1zjhm, jhr1lxdh
FROM "ywdata"."b_per_qskjwcnr"
WHERE zjhm = :zjhm AND jhr1xm IS NOT NULL;
```

### 6.4 API

```
GET /api/graph/person/{zjhm}?depth=1
    → { nodes: [...], edges: [...] }

GET /api/graph/search?keyword=xxx
    → { results: [{id, type, label}] }
```

**返回格式（AntV G6适配）：**
```json
{
  "nodes": [
    {
      "id": "P_440xxx",
      "type": "person",
      "label": "张某",
      "style": { "fill": "#DC2626" },
      "properties": { "risk_score": 72, "age": 16 }
    },
    {
      "id": "C_A440xxx",
      "type": "case",
      "label": "盗窃电动车",
      "style": { "fill": "#7C3AED" },
      "properties": { "ay": "盗窃", "fasj": "2026-03-12" }
    }
  ],
  "edges": [
    {
      "source": "P_440xxx",
      "target": "C_A440xxx",
      "label": "涉嫌",
      "style": { "stroke": "#6B7280" }
    }
  ]
}
```

### 6.5 前端

- 页面: `templates/modules/graph/graph.html`
- 脚本: `static/modules/graph/graph.js`
- 可视化: AntV G6（离线包，放入 `static/vendor/`）
- 交互: 搜索框 + 力导向布局 + 点击展开 + 节点详情侧边栏

---

## 七、共享数据库层

### 7.1 新增 KingBase 连接

```
shared/db/kingbase.py
```

使用 `psycopg2`（KingBase兼容PostgreSQL协议）：

```python
# 核心接口
def get_kb_connection() -> connection
def query_one(sql, params) -> dict
def query_all(sql, params) -> list[dict]
def execute(sql, params) -> int  # affected rows
```

**配置(.env新增)：**
```
KINGBASE_HOST=xxx
KINGBASE_PORT=54321
KINGBASE_DB=xxx
KINGBASE_USER=xxx
KINGBASE_PASSWORD=xxx
```

### 7.2 应用注册

在 `app.py` 中注册新Blueprint：

```python
from modules.score import score_bp
from modules.profile import profile_bp
from modules.dashboard import dashboard_bp
from modules.graph import graph_bp

app.register_blueprint(score_bp, url_prefix='/api/score')
app.register_blueprint(profile_bp, url_prefix='/api/profile')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(graph_bp, url_prefix='/api/graph')
```

---

## 八、前端入口整合

在现有 `templates/index.html` 工作台壳层中新增Tab：

| Tab名称 | 路由 | 模块 |
|---------|------|------|
| 态势总览 | /dashboard | dashboard |
| 个人画像 | /profile | profile |
| 关系图谱 | /graph | graph |

评分模块无独立页面，数据内嵌在画像和面板中。

---

## 九、离线依赖

### Python包

```
psycopg2-binary    # KingBase连接
networkx           # 图计算
```

### 前端离线资源（放入 static/vendor/）

```
antv-g6.min.js     # 图谱可视化
echarts.min.js     # 图表（如已有则复用）
```

---

## 十、演示路径

```
1. 打开【态势总览】
   → 展示全市管控态势：4.5万管控对象、127高风险、案件趋势下降
   → 点击预警列表中的"张某 出现在XX路"

2. 跳转【个人画像】
   → 展示张某全貌：16岁、辍学、单亲、涉案3起、评分72
   → 点击"关系网络"区域的"展开图谱"

3. 跳转【关系图谱】
   → 以张某为中心展开1层关系：3个共犯、2个案件、1个学校
   → 发现3人飙车团伙

4. 从图谱或画像页面点击【下发任务】
   → 对接现有dispatch模块，生成走访任务
   → 完成"感知→研判→打击"闭环
```

---

## 十一、风险与应对

| 风险 | 应对 |
|------|------|
| 数据量大ETL慢 | 先只灌近1年数据，轨迹表只取2026年 |
| 图谱渲染卡顿 | 限制展示节点数<=50，超过提示筛选 |
| 评分算法不合理 | 预留detail_json字段方便调参 |
| 演示时数据为空 | 提前准备3-5个典型案例的完整数据 |
| 离线无法用在线地图 | 用ECharts内置中国地图JSON或纯列表替代 |
