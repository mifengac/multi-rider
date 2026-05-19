# 未成年人智能管控中枢 - 新增功能设计文档

> 主题：打击预防未成年人侵财  
> 比赛：省数字侦查比赛（刑侦方向）  
> 日期：2026-05-17  

---

## 一、现有系统架构概述

```
前端感知(YOLO) → 异常行为检测(飙车/炸街/翘车头) → 人脸识别确认身份 → 省厅系统接口下发任务 → 派出所
```

**现有模块：**
- `modules/detection` - YOLO目标检测（视频/图片上传、任务管理）
- `modules/face` - 人脸识别（人脸库管理、向量比对、身份确认）
- `modules/dispatch` - 任务派发（对接省厅系统接口、短信通知）
- `modules/training` - 模型训练（自动标注、数据集管理）
- `modules/diagnostics` - 诊断服务

---

## 二、新增功能概览

| 序号 | 功能 | 核心价值 | 比赛亮点 |
|------|------|----------|----------|
| 1 | 关系图谱 | 可视化人-案-地-组织关联关系 | 展示侦查思维、串并案能力 |
| 2 | 风险评分 | 量化未成年人犯罪风险等级 | 预测预防能力、数据驱动决策 |
| 3 | 个人画像 | 多维度呈现未成年人全貌 | 全量数据融合分析能力 |
| 4 | 统计面板 | 宏观态势感知与趋势分析 | 整体管控效果可视化 |

---

## 三、数据源梳理

### 3.1 核心业务表（ywdata schema）

#### 案件类

| 表名 | 说明 | 数据量 | 关键字段 |
|------|------|--------|----------|
| `zq_zfba_ajxx` | 执法办案-案件信息 | - | ajxx_ajbh(PK), ajxx_ajmc, ajxx_ay, ajxx_fasj, ajxx_fadd, ajxx_cbdw_mc |
| `zq_zfba_wcnr_ajxx` | 未成年人相关案件 | - | ajxx_ajbh(PK), ajxx_ajmc, ajxx_ay, ajxx_fasj, ajxx_cbdw_mc |
| `zq_zfba_wcnr_shr_ajxx` | 未成年受害人案件 | - | 同上 |
| `b_evt_jjzdbczjajxx` | 110接处警飙车治理案件 | 15,825 | ajbh, wfsj, wfdd, dsrsfzmhm, hphm, wfxw, ay |
| `case_type_config` | 案件类型配置映射 | 14 | leixing, newcharasubclass_list, ay_pattern |

#### 嫌疑人/人员类

| 表名 | 说明 | 数据量 | 关键字段 |
|------|------|--------|----------|
| `zq_zfba_xyrxx` | 执法办案-嫌疑人信息 | - | xyrxx_sfzh(PK), ajxx_join_ajxx_ajbh(FK), xyrxx_xm, xyrxx_csrq, xyrxx_xb, xyrxx_whcd, xyrxx_zy, xyrxx_fzjl |
| `zq_zfba_wcnr_xyr` | 未成年嫌疑人 | - | 同xyrxx结构, 含案件关联 |
| `zq_zfba_qsryxx` | 取保候审人员 | - | qsryxx_sfzh, ajxx_ajbh, qsryxx_ryxm, qsryxx_csrq, qsryxx_nl |
| `zq_zfba_saryxx` | 受案人员(受害人) | - | saryxx_sfzh, ajxx_ajbhs, saryxx_xm, saryxx_csrq, saryxx_shfd |

#### 未成年人专管类

| 表名 | 说明 | 数据量 | 关键字段 |
|------|------|--------|----------|
| `b_per_qscxwcnr` | 全市辍学未成年人 | 1,921 | xm, zjhm, jxqk(就学情况), jtzz, hjdz, yxx(原学校), nj, ssbm |
| `b_per_qskjwcnr` | 全市旷课未成年人(含详细) | 18,812 | xm, zjhm, **fxdj(风险等级)**, jtqk, jhr1xm, jhr1lxdh, jxqk, etlb(儿童类别), knjtlx(困难家庭类型) |
| `b_per_qslswcnr` | 全市流失未成年人 | 36,659 | xm, zjhm, ly(来源) |
| `b_per_qswcnrbczj` | 未成年人飙车治理 | 300 | sfzhm, dsrxm, hphm, wfnr, wfrq, wfdz |
| `b_per_qsyzjszawcnr` | 原有据矫正/戒毒未成年人 | 302 | xm, zjhm, rylx, rydj(人员等级), jtqk, jhrxm, jhrlxfs, ryfl |
| `b_per_qszljscjwcnr` | 残疾未成年人 | 3,031 | (残疾类型+基本信息) |
| `zq_zfba_wcnr_sfzxx` | 未成年人身份证信息 | - | sfzhm, xm, xb, mz, csrq, hjdq, hjdz, jhr, lxdh, yxx, nj, jzyy, whdj |

#### 行为记录类

| 表名 | 说明 | 数据量 | 关键字段 |
|------|------|--------|----------|
| `t_wcnrxwjl_xx` | 未成年人行为记录 | 1,634 | wf_sj, xm, sfzhm, cphm, **wfxw_cn**(违法行为), **blxwlx_cn**(不良行为类型), fsdd |
| `t_jj_bczjwcnr_xx` | 飙车治理未成年人静态库 | 1,581 | xxmcqc, xm, sfzhm, jhr_xm, jhr_sfzhm, **blbxlx**(不良/犯罪类型), blxwlxbm |
| `t_jj_bczjwcnrwf_xx` | 飙车未成年人违法记录 | 2,567 | (违法详细记录) |
| `t_jj_bczjhfb_xx` | 飙车未成年人回访记录 | 2,030 | (回访信息) |

#### 轨迹数据类

| 表名 | 说明 | 数据量 | 关键字段 |
|------|------|--------|----------|
| `b_per_dqqkrygj` | 当前前科人员轨迹 | 317,858 | xm, zjhm, sjhm, **tlkssj/tljssj**(通联起止时间), **jd/wd**(经纬度), ssfj, sspcs, tlwz |
| `t_spy_ryrlgj_xx` | 视频人脸轨迹 | 53,851,207 | face_id, person_id, id_number, name, device_id, **shot_time**, age, face_image |
| `t_ly_checkin_gn` | 旅馆入住记录 | 6,204,216 | (入住人信息+时间+旅馆) |

#### 学校/教育类

| 表名 | 说明 | 数据量 | 关键字段 |
|------|------|--------|----------|
| `b_yfszxxxsxx` | Y市小学学生信息 | 433,945 | xxmc, xsxm, xb, xssfzh, xjzxxdz, jtcyxm, jtcygx, jtcylxdh |
| `sh_gd_zxxxsxj_xx` | X省中小学学生学籍 | 547,217 | (学籍信息) |
| `sh_gd_yeyxsxj_xx` | X省幼儿园学生学籍 | 220,242 | (学籍信息) |
| `sh_fzxxsj_xx` | 法治学校教育学校 | 152 | (学校基本信息) |

#### 人口基础数据

| 表名 | 说明 | 数据量 | 关键字段 |
|------|------|--------|----------|
| `t_ap_czrk_jbxx` | 常住人口基本信息 | 3,828,435 | (人口户籍全量) |
| `t_ap_czrk_zp` | 常住人口照片 | 6,564,739 | (人口照片) |
| `person` | 驾驶人基本信息 | 1,667,371 | (驾驶人) |
| `drivinglicense` | 驾驶证登记信息 | 1,248,673 | (驾驶证) |

### 3.2 任务/专项表（stdata schema - 部分）

| 表名 | 说明 | 关键用途 |
|------|------|----------|
| `b_per_yfblqxwcnrcj` | Y市不良倾向未成年人采集 | 1,809条，不良行为采集建档 |
| `b_per_yfblqxwcnrcj_xwqk` | 行为情况子表 | 1,126条，详细行为描述 |
| `b_per_yfblqxwcnrcj_jhrxx` | 监护人信息子表 | 3,685条，监护关系 |
| `b_per_yfblqxwcnrcj_asjqk` | 案事件情况子表 | 2,181条，关联案件 |
| `b_per_yzblxwwcnrhc` | 原有不良行为未成年人核查 | 3,109条 |
| `b_per_yzblxwwcnrhcjd` | 核查建档 | 782条 |
| `b_loc_fzfxzgz` | 法治防线周边学校 | 558条，学校周边治安 |

---

## 四、功能一：关系图谱

### 4.1 设计目标

构建以**未成年嫌疑人**为中心的多层关系网络，支持：
- 人→案件：一人多案、共同犯罪串并
- 人→人：同案关系、监护关系、同住关系、同校关系
- 人→地点：作案地、居住地、学校、轨迹出没点
- 人→组织/场所：旅馆、网吧、学校、社区矫正机构
- 案件→案件：同类案由串并、时空关联

### 4.2 图谱节点类型

```
节点类型          数据来源                    核心属性
─────────────────────────────────────────────────────────────
Person(人)       zq_zfba_wcnr_xyr           sfzh, xm, csrq, xb, nl
                 zq_zfba_wcnr_sfzxx
                 b_per_qskjwcnr
                 
Case(案件)       zq_zfba_wcnr_ajxx          ajbh, ajmc, ay, fasj, fadd
                 zq_zfba_ajxx
                 b_evt_jjzdbczjajxx

Location(地点)   t_spy_ryrlgj_xx            device_id → 地理位置
                 b_per_dqqkrygj             jd, wd, tlwz
                 案件表的 fadd

School(学校)     b_yfszxxxsxx               xxmc
                 b_per_qscxwcnr             yxx(原学校)
                 sh_fzxxsj_xx

Guardian(监护人) b_per_qskjwcnr             jhr1xm, jhr1lxdh
                 zq_zfba_wcnr_sfzxx         jhr, lxdh
                 b_per_yfblqxwcnrcj_jhrxx

Organization(机构) b_org_fjjssgy            废旧金属收购业
                   t_ly_info                旅馆
```

### 4.3 图谱边类型（关系）

| 关系名称 | 起始节点 | 终止节点 | 数据来源 | 说明 |
|----------|----------|----------|----------|------|
| SUSPECTED_IN | Person | Case | zq_zfba_wcnr_xyr.ajxx_join_ajxx_ajbh | 涉嫌案件 |
| VICTIM_OF | Person | Case | zq_zfba_saryxx.ajxx_ajbhs | 是受害人 |
| CO_SUSPECT | Person | Person | 同案件编号下的不同嫌疑人 | 共同犯罪 |
| GUARDIAN_OF | Guardian | Person | jhr1xm → zjhm | 监护关系 |
| LIVES_AT | Person | Location | hjdz/xzdxz/jtzz | 居住于 |
| COMMITTED_AT | Case | Location | ajxx_fadd / wfdd | 案发地点 |
| STUDIES_AT | Person | School | b_yfszxxxsxx/b_per_qscxwcnr.yxx | 就读于 |
| APPEARED_AT | Person | Location | t_spy_ryrlgj_xx (shot_time+device) | 出现于(人脸轨迹) |
| CHECKED_IN | Person | Organization | t_ly_checkin_gn | 入住旅馆 |
| SAME_SCHOOL | Person | Person | 同校学生 | 同校关系 |
| SAME_AREA | Person | Person | 同辖区/同小区 | 同区域关系 |

### 4.4 前端交互设计

```
┌─────────────────────────────────────────────────────┐
│  关系图谱                                    [全屏] │
├─────────────────────────────────────────────────────┤
│ ┌──────────┐                                        │
│ │ 搜索框   │  身份证/姓名/案件编号                  │
│ └──────────┘                                        │
│                                                     │
│         ┌─────┐                                     │
│    ┌────│ 案1 │────┐                                │
│    │    └─────┘    │                                │
│ ┌──┴──┐         ┌──┴──┐                            │
│ │人物A│─────────│人物B│        图例：               │
│ └──┬──┘         └──┬──┘        ● 人物(蓝)          │
│    │               │           ◆ 案件(红)          │
│ ┌──┴──┐         ┌──┴──┐        ▲ 地点(绿)          │
│ │学校1│         │地点1│        ■ 学校(橙)          │
│ └─────┘         └─────┘                            │
│                                                     │
│ [层级: 1层 2层 3层] [关系筛选▼] [时间范围▼]        │
└─────────────────────────────────────────────────────┘
```

**交互功能：**
- 输入身份证号/姓名/案件编号，以该实体为中心展开图谱
- 支持1-3层关系扩展
- 点击节点显示详情侧边栏
- 支持按关系类型筛选（只看共犯关系、只看轨迹关联等）
- 支持时间范围过滤（近1月/3月/半年/1年）
- 高亮显示风险等级（颜色映射评分）

### 4.5 后端API设计

```
GET  /api/graph/person/{sfzh}?depth=2&relations=all&time_range=6m
     → 返回以人为中心的子图

GET  /api/graph/case/{ajbh}?depth=1
     → 返回以案件为中心的子图

GET  /api/graph/search?keyword=xxx&type=person|case|location
     → 搜索节点

POST /api/graph/expand
     body: { node_id, node_type, direction: "out"|"in"|"both" }
     → 扩展指定节点的关系

GET  /api/graph/paths?from_sfzh=xxx&to_sfzh=yyy&max_hops=4
     → 两人之间的最短路径
```

**返回格式（适配前端图可视化库如ECharts/AntV G6）：**
```json
{
  "nodes": [
    {"id": "P_440xxx", "type": "person", "label": "张某", "properties": {...}, "risk_score": 72},
    {"id": "C_A440xxx", "type": "case", "label": "盗窃案", "properties": {...}}
  ],
  "edges": [
    {"source": "P_440xxx", "target": "C_A440xxx", "type": "SUSPECTED_IN", "properties": {...}}
  ]
}
```

### 4.6 技术方案

**方案选择：基于SQL + 内存图计算（不引入图数据库）**

理由：
- 比赛环境有限，避免引入Neo4j等额外依赖
- 数据量可控（活跃未成年人管控对象数千级别）
- 用SQL联表查询构建子图，Python端做路径计算

```python
# 核心模块结构
modules/graph/
├── __init__.py
├── routes.py              # API路由
├── services/
│   ├── __init__.py
│   ├── graph_builder.py   # 图构建(SQL查询→节点/边)
│   ├── relation_engine.py # 关系发现引擎
│   └── path_finder.py    # 路径搜索(BFS/DFS)
└── models/
    ├── __init__.py
    └── graph_models.py    # 节点/边数据模型
```

---

## 五、功能二：风险评分系统

### 5.1 设计目标

基于多维度数据为每位管控未成年人生成动态风险评分（0-100），辅助警务人员优先处理高风险对象。

### 5.2 评分维度与权重

| 维度 | 权重 | 数据来源 | 评分逻辑 |
|------|------|----------|----------|
| 案件关联 | 30% | zq_zfba_wcnr_xyr, b_evt_jjzdbczjajxx | 涉案次数、案件严重程度、案由类型 |
| 行为记录 | 25% | t_wcnrxwjl_xx, t_jj_bczjwcnrwf_xx | 违法次数、行为类型(飙车/盗窃/斗殴)、近期频率 |
| 家庭环境 | 20% | b_per_qskjwcnr | 监护缺失(fmsftswc)、困难家庭(knjtlx)、父母外出务工 |
| 教育状态 | 15% | b_per_qscxwcnr, b_per_qskjwcnr.jxqk | 辍学/旷课/流失、就学情况 |
| 社交网络 | 10% | 图谱共犯关系 + 轨迹共现 | 高风险同伴数量、团伙关联度 |

### 5.3 评分细则

#### 5.3.1 案件关联评分（满分30分）

```
base_score = 0

# 涉案次数
case_count = 涉案案件数
if case_count == 0: base_score += 0
elif case_count == 1: base_score += 8
elif case_count == 2: base_score += 15
elif case_count >= 3: base_score += 22

# 案件严重程度加分
for each case:
    if 案由 in ['抢劫', '抢夺', '故意伤害']: base_score += 4
    elif 案由 in ['盗窃', '诈骗']: base_score += 3
    elif 案由 in ['寻衅滋事', '聚众斗殴']: base_score += 2

# 时效衰减：超过1年的案件权重减半
cap at 30
```

#### 5.3.2 行为记录评分（满分25分）

```
# 违法行为次数
violation_count = 行为记录数
time_decay = 近3月记录权重x1.5, 3-6月x1.0, 6月以上x0.5

# 行为类型严重度
severity_map = {
    '飙车': 5, '盗窃': 5, '斗殴': 4, 
    '寻衅滋事': 4, '损毁财物': 3, '翘课聚集': 2
}

score = sum(severity * time_decay for each record)
cap at 25
```

#### 5.3.3 家庭环境评分（满分20分）

```
score = 0
if 父母双方外出务工: score += 8
elif 单亲外出: score += 5

if 困难家庭(低保/边缘): score += 5
if 监护人缺失/无监护能力: score += 10
if 家庭暴力/吸毒记录: score += 6

cap at 20
```

#### 5.3.4 教育状态评分（满分15分）

```
if 辍学: score = 15
elif 旷课(频繁): score = 10
elif 旷课(偶尔): score = 6
elif 流失(去向不明): score = 13
elif 正常在校: score = 0
```

#### 5.3.5 社交网络评分（满分10分）

```
high_risk_contacts = 图谱中与其关联的高风险人数(score>60)
gang_relation = 是否有3人以上共同犯罪

score = min(high_risk_contacts * 3, 7)
if gang_relation: score += 3
cap at 10
```

### 5.4 风险等级映射

| 分数区间 | 等级 | 颜色 | 管控建议 |
|----------|------|------|----------|
| 80-100 | 极高风险 | 红色 | 重点监控、每周走访、联合教育部门干预 |
| 60-79 | 高风险 | 橙色 | 定期走访(2周)、关注轨迹异动 |
| 40-59 | 中风险 | 黄色 | 每月走访、学校协同关注 |
| 20-39 | 低风险 | 蓝色 | 季度走访、常规关注 |
| 0-19 | 基本正常 | 绿色 | 纳入基础管理 |

### 5.5 动态更新机制

- **实时触发**：新增案件/违法记录时立即重算
- **定时批量**：每日凌晨全量重算一次
- **衰减机制**：无新增违法记录时每月自动衰减2分

### 5.6 API设计

```
GET  /api/score/{sfzh}
     → 返回某人当前评分及各维度明细

GET  /api/score/list?min_score=60&area=xxx&sort=desc&page=1&size=20
     → 高风险人员列表

GET  /api/score/trend/{sfzh}?months=12
     → 某人近12月评分趋势

POST /api/score/batch-recalculate
     → 触发全量重算
```

### 5.7 模块结构

```python
modules/score/
├── __init__.py
├── routes.py
├── services/
│   ├── __init__.py
│   ├── score_engine.py       # 评分引擎(组装各维度)
│   ├── dimension_case.py     # 案件维度计算
│   ├── dimension_behavior.py # 行为维度计算
│   ├── dimension_family.py   # 家庭维度计算
│   ├── dimension_education.py# 教育维度计算
│   ├── dimension_social.py   # 社交维度计算(依赖graph模块)
│   └── score_store.py        # 评分结果存储/缓存
└── models/
    └── score_models.py
```

---

## 六、功能三：个人画像

### 6.1 设计目标

为每个管控对象生成**一页式**综合画像，整合所有数据维度，辅助办案人员快速了解对象全貌。

### 6.2 画像结构

```
┌───────────────────────────────���────────────────────────────────┐
│ ┌──────┐  张某某 (男, 16岁)                 风险评分: 72/100   │
│ │ 照片 │  身份证: 440XXXXXXXXXXXXXXX        ████████░░ [高风险]│
│ │      │  户籍: XX市XX区XX街道                                  │
│ └──────┘  现住: XX市XX路XX号                                    │
│           学校: XX中学(已辍学)  监护人: 张某父(139XXXX)         │
├───────────┬────────────────────────────────────────────────────┤
│ 基本信息  │ 民族: 汉 | 文化: 初中 | 户籍: 城镇                │
│           │ 家庭: 单亲(母亲外出务工) | 经济: 低保边缘户         │
│           │ 监护状态: 祖父代管 | 监护人联系: 139XXXXXXXX        │
├───────────┼────────────────────────────────────────────────────┤
│ 涉案记录  │ 2026-03-12 盗窃电动车 (XX派出所) [已结案]          │
│ (3起)     │ 2025-11-20 寻衅滋事 (XX派出所) [行政处罚]          │
│           │ 2025-08-05 故意损毁财物 (XX派出所) [训诫]           │
├───────────┼────────────────────────────────────────────────────┤
│ 行为记录  │ 2026-04-28 飙车(XX路段) 车牌:粤BXXXX              │
│ (5条)     │ 2026-03-01 夜间聚集(XX网吧周边)                    │
│           │ 2025-12-15 旷课(连续3天)                           │
├───────────┼────────────────────────────────────────────────────┤
│ 轨迹分析  │ [热力图] 高频出现: XX路口, XX网吧, XX商场           │
│           │ 最近出现: 2026-05-16 14:32 XX路与XX路交叉口          │
│           │ 活动规律: 夜间活跃(22:00-02:00占比45%)             │
├───────────┼────────────────────────────────────────────────────┤
│ 关系网络  │ [迷你图谱] 关联人员: 李某(共犯x2), 王某(同校)      │
│           │ 团伙识别: 3人飙车团伙(张某/李某/赵某)              │
├───────────┼────────────────────────────────────────────────────┤
│ 评分明细  │ 案件:22 行为:18 家庭:16 教育:12 社交:4 = 总分72    │
│           │ [趋势图] 近6月评分趋势: 55→62→68→72 ↑             │
├───────────┼────────────────────────────────────────────────────┤
│ 管控建议  │ 1. 建议联合教育部门劝返复学                        │
│           │ 2. 加强夜间巡逻XX路段                              │
│           │ 3. 走访监护人(祖父),告知近期违法情况               │
│           │ 4. 注意团伙聚集预警                                │
└───────────┴────────────────────────────────────────────────────┘
```

### 6.3 数据聚合SQL逻辑

```sql
-- 画像数据聚合(伪代码)
WITH person AS (
    SELECT * FROM ywdata.zq_zfba_wcnr_sfzxx WHERE sfzhm = :sfzh
),
cases AS (
    SELECT * FROM ywdata.zq_zfba_wcnr_ajxx a
    JOIN ywdata.zq_zfba_wcnr_xyr x ON x.ajxx_join_ajxx_ajbh = a.ajxx_ajbh
    WHERE x.xyrxx_sfzh = :sfzh
),
behaviors AS (
    SELECT * FROM ywdata.t_wcnrxwjl_xx WHERE sfzhm = :sfzh ORDER BY wf_sj DESC
),
trajectory AS (
    SELECT * FROM ywdata.t_spy_ryrlgj_xx WHERE id_number = :sfzh
    ORDER BY shot_time DESC LIMIT 100
),
education AS (
    SELECT 'dropout' as status, * FROM ywdata.b_per_qscxwcnr WHERE zjhm = :sfzh
    UNION ALL
    SELECT 'truant' as status, * FROM ywdata.b_per_qskjwcnr WHERE zjhm = :sfzh
),
family AS (
    SELECT * FROM ywdata.b_per_qskjwcnr WHERE zjhm = :sfzh  -- 含详细家庭信息
)
-- 组装为画像JSON
```

### 6.4 API设计

```
GET  /api/profile/{sfzh}
     → 完整个人画像

GET  /api/profile/{sfzh}/trajectory?days=30
     → 近30天轨迹详情

GET  /api/profile/{sfzh}/timeline
     → 时间轴(案件+行为+轨迹混合排序)

GET  /api/profile/{sfzh}/photo
     → 人口照片(从t_ap_czrk_zp获取)
```

### 6.5 模块结构

```python
modules/profile/
├── __init__.py
├── routes.py
├── services/
│   ├── __init__.py
│   ├── profile_assembler.py   # 画像数据聚合
│   ├── trajectory_service.py  # 轨迹分析(热力图/活动规律)
│   ├── timeline_service.py    # 时间轴生成
│   └── suggestion_engine.py   # 管控建议生成(规则引擎)
└── models/
    └── profile_models.py
```

---

## 七、功能四：统计面板（Dashboard）

### 7.1 设计目标

宏观展示全市未成年人侵财犯罪态势，支撑指挥决策。

### 7.2 面板布局

```
┌──────────────────────────────────────────────────────────────────┐
│  未成年人智能管控中枢 - 态势总览                    2026-05-17   │
├──────────┬──────────┬──────────┬──────────┬───────────────────────┤
│ 管控总人数│ 高风险   │ 本月新增案│ 本月走访 │                       │
│  1,921   │   127    │    23    │   456    │   [全市地图热力图]     │
│  ↑3.2%   │  ↓5.2%   │  ↑12%   │  达标89% │   案件/人员分布       │
├──────────┴──────────┴──────────┴──────────┤                       │
│                                            │                       │
│ [案件类型分布-饼图]    [月度趋势-折线图]   │                       │
│  盗窃 45%              涉案人数趋势        │                       │
│  抢夺 18%              案件数趋势          │                       │
│  诈骗 12%              风险评分趋势        │                       │
│  其他 25%                                  │                       │
├────────────────────────────────────────────┼───────────────────────┤
│                                            │  [辖区排名-柱状图]    │
│ [风险等级分布-环形图]                      │   XX分局: 23人        │
│  极高: 12人(红)                            │   XX分局: 19人        │
│  高:   115人(橙)                           │   XX分局: 15人        │
│  中:   340人(黄)                           │   ...                 │
│  低:   892人(蓝)                           │                       │
│  正常: 562人(绿)                           │                       │
├────────────────────────────────────────────┼───────────────────────┤
│ [预警列表 - 实时滚动]                      │  [年龄/性别分布]      │
│  14:32 张某 出现在XX路(高风险区域)         │  14岁以下: 12%        │
│  13:45 飙车预警: XX路段3人聚集             │  14-16岁: 58%         │
│  12:10 李某 旅馆入住(无监护人陪同)         │  16-18岁: 30%         │
│  ...                                       │  男: 82% 女: 18%     │
└────────────────────────────────────────────┴───────────────────────┘
```

### 7.3 核心指标

| 指标 | 计算逻辑 | 数据源 |
|------|----------|--------|
| 管控总人数 | 辍学+旷课+流失+涉案去重 | b_per_qscxwcnr + b_per_qskjwcnr + b_per_qslswcnr + zq_zfba_wcnr_xyr |
| 高风险人数 | 评分>=60的人数 | score模块 |
| 本月新增案件 | 本月fasj的未成年人侵财案件 | zq_zfba_wcnr_ajxx WHERE fasj >= 本月1号 |
| 案件类型分布 | 按案由分组统计 | zq_zfba_wcnr_ajxx.ajxx_ay |
| 辖区分布 | 按承办单位分组 | ajxx_cbdw_mc / sspcs |
| 月度趋势 | 按月统计案件数/涉案人数 | 按ajxx_fasj月度GROUP BY |
| 风险等级分布 | 按评分区间统计 | score模块 |
| 年龄分布 | 当前年龄 = 当年 - 出生年 | csrq字段 |
| 活动时段分析 | 违法/出现时间分布 | t_wcnrxwjl_xx.wf_sj, t_spy_ryrlgj_xx.shot_time |

### 7.4 实时预警规则

| 预警类型 | 触发条件 | 来源 |
|----------|----------|------|
| 高风险人员出现 | 评分>=80的人出现在人脸抓拍 | t_spy_ryrlgj_xx实时接入 |
| 夜间聚集 | 22:00后同一设备周边3+高风险人员 | 人脸轨迹时空聚类 |
| 异常旅馆入住 | 未成年人无监护人陪同入住 | t_ly_checkin_gn实时接入 |
| 飙车预警 | YOLO模型检测到飙车行为 | 现有detection模块 |
| 学校周边异常 | 高风险人员出现在学校200m范围 | 人脸轨迹+学校坐标匹配 |

### 7.5 API设计

```
GET  /api/dashboard/summary
     → 核心指标汇总(总人数、高风险数、案件数等)

GET  /api/dashboard/trend?months=12&metric=cases|persons|score
     → 月度趋势数据

GET  /api/dashboard/distribution?dimension=case_type|risk_level|area|age|gender
     → 各维度分布数据

GET  /api/dashboard/alerts?limit=20
     → 最近预警列表

GET  /api/dashboard/heatmap?days=30
     → 案件/人员热力图数据(经纬度+权重)

GET  /api/dashboard/ranking?by=area|school&metric=case_count|risk_count
     → 辖区/学校排名
```

### 7.6 模块结构

```python
modules/dashboard/
├── __init__.py
├── routes.py
├── services/
│   ├── __init__.py
│   ├── summary_service.py    # 汇总指标
│   ├── trend_service.py      # 趋势分析
│   ├── distribution_service.py # 分布统计
│   ├── alert_service.py      # 预警服务
│   └── heatmap_service.py    # 热力图数据
└── models/
    └── dashboard_models.py
```

---

## 八、整体模块依赖关系

```
                    ┌──────────────┐
                    │  Dashboard   │
                    │  (统计面板)   │
                    └──────┬───────┘
                           │ 依赖
              ┌────────────┼────────────┐
              ▼            ▼            ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │  Score   │  │  Graph   │  │ Profile  │
      │ (评分)   │  │ (图谱)   │  │ (画像)   │
      └────┬─────┘  └────┬─────┘  └────┬─────┘
           │              │              │
           │    ┌─────────┘              │
           │    │                        │
           ▼    ▼                        ▼
      ┌──────────────────────────────────────┐
      │        shared/db/kingbase.py         │  ← 新增KingBase连接层
      │        (ywdata/stdata schema查询)     │
      └──────────────────────────────────────┘
              ▲            ▲            ▲
              │            │            │
      ┌───────┘     ┌─────┘     ┌──────┘
      │             │            │
┌─────────┐  ┌──────────┐  ┌──────────┐
│Detection│  │   Face   │  │ Dispatch │    ← 现有模块
│ (YOLO)  │  │ (人脸)   │  │ (派发)   │
└─────────┘  └──────────┘  └──────────┘
```

---

## 九、数据库连接说明

当前系统已有Oracle连接（`shared/db/oracle.py`），生产数据库为**KingBase**（人大金仓，PostgreSQL兼容）。

需新增 `shared/db/kingbase.py`，主要查询 `ywdata` 和 `stdata` schema下的表。

**连接配置（.env）：**
```
KINGBASE_HOST=xxx
KINGBASE_PORT=54321
KINGBASE_DB=xxx
KINGBASE_USER=xxx
KINGBASE_PASSWORD=xxx
KINGBASE_SCHEMA=ywdata
```

由于KingBase兼容PostgreSQL协议，可直接使用 `psycopg2` 驱动。

---

## 十、前端技术选型建议

| 功能 | 推荐方案 | 备注 |
|------|----------|------|
| 图谱可视化 | AntV G6 或 ECharts Graph | G6更适合交互式图谱 |
| 统计图表 | ECharts | 已有成熟经验 |
| 热力图/地图 | 高德地图 / Leaflet | 轨迹+热力叠加 |
| 画像页面 | 原生HTML + Tailwind | 保持现有技术栈 |
| 实时预警 | WebSocket / SSE | 推送实时消息 |

---

## 十一、实施优先级

考虑比赛时间紧迫，建议按以下顺序实施：

| 优先级 | 功能 | 预估工作量 | 理由 |
|--------|------|------------|------|
| P0 | 统计面板 | 2天 | 展示效果直观，能快速体现系统价值 |
| P0 | 个人画像 | 2天 | 核心展示页，数据聚合逻辑清晰 |
| P1 | 风险评分 | 1.5天 | 为画像和面板提供核心数据支撑 |
| P1 | 关系图谱 | 2.5天 | 技术亮点最高，但开发量较大 |

**建议实施顺序：评分 → 画像 → 统计面板 → 图谱**

评分模块是画像和面板的基础数据，应最先完成。图谱虽然最出彩但开发量最大，可先做简化版（只展示1层直接关系）。

---

## 十二、比赛展示建议

1. **演示路径**：统计面板(宏观态势) → 点击高风险人员 → 个人画像(微观详情) → 展开图谱(关系分析) → 发现团伙 → 下发任务
2. **亮点话术**：
   - "数据驱动的风险预测" - 评分系统
   - "多维数据融合的全息画像" - 个人画像
   - "关系图谱辅助串并案" - 关系图谱
   - "前端感知+智能研判+精准打击的闭环" - 整体流程
3. **关键数据**：展示真实的数据量级（5300万+视频轨迹、380万+人口数据等）

---

## 附录：关键表字段中文对照

| 缩写 | 含义 | 缩写 | 含义 |
|------|------|------|------|
| ajxx | 案件信息 | xyrxx | 嫌疑人信息 |
| ajbh | 案件编号 | sfzh/sfzhm/zjhm | 身份证号 |
| ajmc | 案件名称 | xm | 姓名 |
| ay | 案由 | csrq | 出生日期 |
| fasj | 发案时间 | xb | 性别 |
| fadd | 发案地点 | mz | 民族 |
| cbdw | 承办单位 | whcd | 文化程度 |
| fxdj | 风险等级 | jhr | 监护人 |
| wfxw | 违法行为 | hjdz | 户籍地址 |
| blxwlx | 不良行为类型 | jxqk | 就学情况 |
| wcnr | 未成年人 | bczj | 飙车治理 |
| qsryxx | 取保人员信息 | saryxx | 受案人员信息 |
