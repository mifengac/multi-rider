# 📋 设计方法论答疑 —— 针对你的具体情况逐条分析

> 本文档是对 [project_design_methodology.md](./project_design_methodology.md) 的补充答疑，
> 结合你当前项目的**实际代码结构、部署环境、数据库情况**进行针对性分析。

---

## 问题一：「高内聚」到底是什么意思？

### 1.1 一句话解释

> **高内聚 = 一个模块只干一件事，并且把这件事干完整。**

它和「低耦合」是一对搭档：

| 概念 | 一句话 | 生活比喻 |
|------|--------|---------|
| **高内聚** | 模块内部的东西彼此紧密相关 | 厨房里只放做饭的东西，不放被子枕头 |
| **低耦合** | 模块之间尽量少地互相依赖 | 厨房坏了不影响卧室睡觉 |

### 1.2 用你项目的真实代码举例

看你现在的 `modules/` 目录划分：

```
modules/
├── detection/     ← 二轮车目标检测
├── face/          ← 人脸识别
├── dispatch/      ← 任务派发 / 短信
└── training/      ← 模型训练
```

**这个划分本身就是「高内聚」的体现**——按业务领域把相关代码聚在一起。

#### ✅ 高内聚的好例子（你已经做到了）

```
modules/face/
├── routes.py                          ← 人脸相关的路由
├── services/
│   ├── identity_service.py            ← 人脸比对逻辑
│   └── library_task_service.py        ← 人脸库管理逻辑
└── sql/                               ← 人脸相关的SQL
```

人脸模块里面的文件全都围绕「人脸识别」这一个主题。路由、服务、SQL 三者紧密配合。
**这就是高内聚**——模块内的代码关系密切，共同完成一个完整的业务功能。

#### ❌ 低内聚的反面例子（假设的，帮你理解）

如果你把代码组织成这样：

```
utils/
├── db_utils.py          ← 里面既有人脸SQL、又有检测SQL、又有派发SQL
├── image_utils.py       ← 里面既有人脸图片处理、又有检测图片处理
└── task_utils.py        ← 里面既有训练任务、又有检测任务、又有派发任务
```

这就是**低内聚**——一个文件里塞了不相关的功能，改人脸的时候可能会误改到检测的代码。

### 1.3 判断内聚度的简单方法

问自己一个问题：

> **「如果我要删掉人脸识别功能，我需要改几个目录下的代码？」**

- 如果只需要删 `modules/face/` 这一个目录 → **高内聚** ✅
- 如果还要去 `modules/detection/`、`shared/utils/` 等处处删代码 → **低内聚** ❌

### 1.4 你的项目目前的内聚度评估

| 模块 | 内聚度 | 说明 |
|------|--------|------|
| `modules/face/` | ⭐⭐⭐⭐ 良好 | 路由、服务、SQL 自成一体 |
| `modules/training/` | ⭐⭐⭐⭐ 良好 | 训练相关逻辑集中 |
| `modules/dispatch/` | ⭐⭐⭐⭐ 良好 | 派发逻辑自包含 |
| `modules/detection/` | ⭐⭐⭐ 一般 | 路由文件较大（`job_routes.py` 12KB），可以进一步拆分服务层 |
| `shared/` | ⭐⭐⭐ 一般 | 公共层合理，但需注意别变成「垃圾桶」 |

> [!TIP]
> **总结**：高内聚不是一个高深概念，就是「相关的代码放一起，不相关的分开」。
> 你的项目模块划分已经做得不错了，保持这个意识继续往下走就行。

---

## 问题二：从 Windows 10 迁移到 Ubuntu 22 虚拟机

### 2.1 你的部署现状和目标

```
当前状态                              目标状态
─────────────                        ─────────────
Windows 10 内网电脑                   Ubuntu 22.04 LTS 虚拟机
uv 直接运行                          16核 CPU / 16GB 内存 / 500GB 硬盘
一个人维护                            一个人维护（不变）
手动启动 app.py + worker.py           需要稳定、自动恢复运行
```

### 2.2 先解释：什么是 systemd？

> **systemd 就是 Linux 系统自带的"进程管家"。**

| 概念 | Windows 类比 | 作用 |
|------|-------------|------|
| **systemd** | Windows 服务管理器（services.msc） | 管理后台进程的启动、停止、开机自启、崩溃重启 |
| **systemd 裸跑** | 直接在 Windows 上用 `python app.py` 运行，不套 Docker | 不用 Docker 容器，直接在操作系统上运行 Python 程序，用 systemd 让它自动启动和崩溃恢复 |

简单说：
- **Docker 部署** = 把你的程序装进一个"集装箱"（容器）里运行
- **systemd 裸跑** = 程序直接在操作系统上运行，用系统自带工具管理进程

### 2.3 关键信息：你的内网无互联网

你提到了几个关键事实：

```
事实1：内网无互联网
事实2：Windows 上安装依赖是用 wheel 打包 → U盘传入 → uv 离线安装
事实3：Ubuntu 上还没装 uv / Python 环境
事实4：你有 Ubuntu + Docker 的部署经验
```

这完全改变了我之前的建议。让我重新对比两种方案：

### 2.4 方案对比（修正版）

| 对比项 | systemd 裸跑 | Docker 部署 |
|--------|-------------|-------------|
| **离线安装复杂度** | ⚠️ **很麻烦** | ✅ **简单** |
| | 要在 Ubuntu 上离线装 Python 3.10+ | 只需要一个 `.tar` 镜像文件 |
| | 要离线装 uv | 不需要 uv |
| | 要一个个搬 wheel 包 | 所有依赖都在镜像里 |
| | 要装系统级依赖（libaio1 等） | 镜像里已经装好了 |
| **Oracle Instant Client** | 要手动配置 LD_LIBRARY_PATH | Dockerfile 里已经配好了 |
| **你的经验** | 没用过 systemd（需要学） | **用过 Docker ✅** |
| **更新代码** | 重新搬 wheel、改文件 | 重新导入镜像，重启容器 |
| **崩溃恢复** | 需要额外写 systemd 配置 | `restart: unless-stopped` 已经写好了 |

> [!IMPORTANT]
> **修正建议：直接用 Docker，不要用 systemd 裸跑。**
>
> 之前我建议先用 systemd，是假设你能联网装依赖。
> 既然内网无互联网 + 你有 Docker 经验，Docker 反而是**最省事的方案**。
> 因为你可以在有网的电脑上构建好镜像，打包成一个文件传进内网，一条命令就跑起来。

### 2.5 Docker 离线部署完整流程

整个流程分两个环境：

```
┌─────────────────────────┐         U盘/SCP         ┌──────────────────────────┐
│  外网电脑（能上网）       │  ──────────────────→    │  内网 Ubuntu 22 虚拟机    │
│                         │   传输 .tar 镜像文件      │                          │
│  1. 构建 Docker 镜像     │                         │  3. 导入镜像              │
│  2. 导出为 .tar 文件     │                         │  4. docker compose up     │
└─────────────────────────┘                         └──────────────────────────┘
```

#### 步骤1：在有网的电脑上构建镜像

你需要一台能联网的、装了 Docker 的电脑（Linux / Mac / Windows + Docker Desktop 都行）。

```bash
# 1. 把整个项目目录拷贝到有网的电脑上
# （包括 model/ 和 instantclient_11_2/ 目录）

# 2. 构建 Docker 镜像
cd /path/to/multi-rider
sudo docker build -t multi-rider:latest -f ops/Dockerfile .

# 构建过程会自动：
#   - 下载 Python 3.10 基础镜像
#   - 安装系统依赖（libaio1 等）
#   - pip 安装所有 Python 包（torch CPU 版、ultralytics 等）
#   - 拷贝你的代码、模型、Oracle Instant Client
# 整个过程大约需要 10-20 分钟（取决于网速）
```

#### 步骤2：导出镜像为文件

```bash
# 导出为 tar 文件（大约 3-6GB，取决于模型大小）
sudo docker save multi-rider:latest -o multi-rider-image.tar

# 可选：压缩一下，能小不少
gzip multi-rider-image.tar
# 生成 multi-rider-image.tar.gz（通常能压缩到原来的 60-70%）
```

#### 步骤3：传入内网并导入

```bash
# 用 U 盘或 scp 把 multi-rider-image.tar.gz 传到 Ubuntu 虚拟机

# 在 Ubuntu 虚拟机上导入镜像
gunzip multi-rider-image.tar.gz                    # 如果压缩了的话
sudo docker load -i multi-rider-image.tar

# 验证镜像已导入
sudo docker images | grep multi-rider
# 应该看到：multi-rider   latest   xxxxxxxx   3.5GB
```

#### 步骤4：启动服务

```bash
# 1. 把项目的 docker-compose.yml 和 env 文件拷贝到 Ubuntu 上
mkdir -p /opt/multi-rider
# 拷贝以下文件到 /opt/multi-rider/：
#   - docker-compose.yml
#   - ops/app.env.ubuntu.example → 改名为 app.env 并修改配置

# 2. 编辑 app.env（数据库连接等）
cd /opt/multi-rider
cp app.env.ubuntu.example app.env
nano app.env    # 修改 Oracle、KingbaseV8 连接信息等

# 3. 创建数据目录
mkdir -p runtime/{data,output,datasets,face_data,train_runs,upload_tmp}

# 4. 一键启动！
sudo docker compose up -d

# 5. 查看运行状态
sudo docker compose ps
sudo docker compose logs -f        # 看实时日志
sudo docker compose logs -f web    # 只看 Web 日志
sudo docker compose logs -f worker # 只看 Worker 日志
```

### 2.6 日常运维命令速查

等你部署好之后，日常只需要这几条命令：

```bash
# 查看状态
sudo docker compose ps

# 看日志（排查问题时用）
sudo docker compose logs -f

# 重启服务
sudo docker compose restart

# 停止服务
sudo docker compose down

# 更新代码后重新部署
# （在有网电脑上重新 build → save → 传入内网 → load）
sudo docker compose down
sudo docker load -i multi-rider-image-v2.tar
sudo docker compose up -d
```

### 2.7 迁移注意事项

| 注意项 | 说明 |
|--------|------|
| **Docker 本身** | Ubuntu 22 虚拟机需要预装 Docker，让科技信息部门帮你装好（`apt install docker.io docker-compose-plugin`），或者你自己离线装 |
| **Oracle Instant Client** | 你的 Dockerfile 里已经处理了（从 `instantclient_11_2/` 目录 COPY 进去），确保这个目录里有 Linux 版的 `.so` 文件 |
| **Linux 版 Instant Client** | 构建镜像时，`instantclient_11_2/` 目录里必须是 **Linux 版本**的文件（`.so` 结尾），不能用 Windows 版的 `.dll` 文件 |
| **KingbaseV8** | `psycopg2-binary` 在 Docker 镜像中会自动安装好，只需要在 `app.env` 里配置连接字符串 |
| **模型文件** | `model/` 目录下的 `.pt` 文件会被打包进镜像（Dockerfile 第49行 `COPY model ./model`） |
| **持久化数据** | `docker-compose.yml` 已经配好了 volumes 挂载，数据存在宿主机 `runtime/` 目录，不会因为容器重启丢失 |
| **网络连通性** | 确保 Ubuntu 虚拟机能访问 KingbaseV8 和 Oracle 11g 服务器（同一内网应该没问题） |

### 2.8 16核16G 的资源规划建议

你的虚拟机配置对这个项目来说非常充裕：

```
总资源：16核 CPU / 16GB 内存 / 500GB 硬盘

Docker 引擎开销：       ~1 核 / ~256MB 内存      ← 很轻量
Web 容器 (app.py)：     ~1-2 核 / ~512MB 内存     ← 很轻量
Worker 容器 (worker.py)：~8-12 核 / ~4-8GB 内存    ← 模型推理/训练时吃资源
系统 + 余量：            ~2-4 核 / ~4-8GB 内存

硬盘使用估算：
  系统 + Docker：       ~10GB
  Docker 镜像：         ~4-6GB
  数据集 + 训练产出：   ~50-200GB（取决于数据量）
  剩余空间：           ~280-430GB   ← 非常充足
```

> [!IMPORTANT]
> **总结：你的情况用 Docker 是最优解。**
>
> 原因：
> 1. 内网无互联网 → 在 Ubuntu 上离线装 Python + uv + 几十个包很痛苦，Docker 镜像一个文件搞定
> 2. 你有 Docker 经验 → 没有学习成本
> 3. Dockerfile 和 docker-compose.yml 都已经写好了 → 直接用
> 4. Docker 自带进程管理（崩溃自启、开机自启）→ 不需要额外配 systemd
>
> **systemd 裸跑虽然更"轻量"，但在无网环境下反而更麻烦。**

---

## 问题三：数据库架构的实际情况

### 3.1 你的数据库现状梳理

根据你的描述，实际数据库架构是这样的：

```
┌─────────────────────────────────────────────────────────────┐
│                     你的项目 (multi-rider)                    │
│                                                             │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐     │
│  │ SQLite 本地  │   │ KingbaseV8   │   │ Oracle 11g   │     │
│  │ (自建)      │   │ (部门主库)    │   │ (共用服务器)  │     │
│  │             │   │              │   │              │     │
│  │ • 任务队列   │   │ • 人脸照片    │   │ DB1:卡口照片  │     │
│  │ • 作业状态   │   │ • 基础数据    │   │ DB2:短信平台  │     │
│  │ • 训练记录   │   │              │   │              │     │
│  └─────────────┘   └──────────────┘   └──────────────┘     │
│    你完全控制         只读查询           只读查询 + 写入短信   │
│                      (人家的库)         (人家的库)           │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 之前分析文档的修正

之前的 `project_design_methodology.md` 里写的架构图只提到了 Oracle DB，没有体现 KingbaseV8。现在根据你的实际情况修正：

| 数据库 | 类型 | 用途 | 你的权限 | 驱动 |
|--------|------|------|---------|------|
| **SQLite** | 本地嵌入式 | 任务队列、作业状态、训练记录 | 完全控制 | Python 内置 `sqlite3` |
| **KingbaseV8** | 部门主库 | 人脸照片数据源 | 只读（推测） | `psycopg2`（兼容 PG 协议） |
| **Oracle 11g - DB1** | 卡口业务库 | 二轮车卡口照片 | 只读 | `oracledb` |
| **Oracle 11g - DB2** | 短信平台库 | 短信下发 | 读写 | `oracledb` |

### 3.3 这种架构其实很常见也很合理

你的项目是一个**「对接型应用」**——自己不拥有核心数据，而是从多个已有系统中采集数据进行分析。这在公安信息化项目中非常典型。

需要注意的几点：

#### 连接管理

```python
# 建议的连接管理方式：
# 1. KingbaseV8 用 psycopg2 连接池
import psycopg2.pool

kb_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1, maxconn=5,
    host="kingbase_host", port=54321,
    database="main_db", user="readonly_user", password="***"
)

# 2. Oracle 用 oracledb 连接池
import oracledb

oracle_pool = oracledb.create_pool(
    user="user", password="***",
    dsn="oracle_host:1521/service_name",
    min=1, max=5
)
```

#### 迁移到 Ubuntu 时的注意事项

| 数据库 | Windows → Ubuntu 要改的 |
|--------|----------------------|
| SQLite | 不需要改，跨平台 |
| KingbaseV8 | `psycopg2-binary` 在 Linux 上直接 pip 安装即可，可能比 Windows 更容易 |
| Oracle 11g | 需要下载 **Linux 版** Oracle Instant Client 11.2，Windows 版不能用 |

> [!WARNING]
> **Oracle Instant Client 是迁移时最可能踩坑的地方。**
> 确保下载的是 `instantclient-basic-linux.x64-11.2.0.4.0.zip`，解压后设置好 `LD_LIBRARY_PATH`。
> 另外 `libaio1` 这个系统包必须安装：`sudo apt install libaio1`

---

## 问题四：浏览器兼容性（Chrome 88 / 109）

### 4.1 影响范围分析

Chrome 88（2021年1月）和 Chrome 109（2023年1月）都不算太老，大部分现代 Web 特性都已支持：

| 特性 | Chrome 88 | Chrome 109 | 你需要关注吗？ |
|------|-----------|------------|--------------|
| ES6 (let/const/箭头函数) | ✅ | ✅ | 不用担心 |
| Fetch API | ✅ | ✅ | 不用担心 |
| CSS Grid / Flexbox | ✅ | ✅ | 不用担心 |
| CSS 变量 (custom properties) | ✅ | ✅ | 不用担心 |
| Optional Chaining (?.) | ✅ | ✅ | 不用担心 |
| Nullish Coalescing (??) | ✅ | ✅ | 不用担心 |
| Top-level await | ❌ | ✅ | ⚠️ 避免使用 |
| CSS Container Queries | ❌ | ❌ | ⚠️ 避免使用 |
| CSS :has() 选择器 | ❌ | ❌ | ⚠️ 避免使用 |
| View Transitions API | ❌ | ❌ | ⚠️ 避免使用 |
| dialog 元素 | ⚠️ 部分 | ✅ | ⚠️ 谨慎使用 |
| structuredClone() | ❌ | ✅ | ⚠️ 用 JSON 深拷贝代替 |

### 4.2 对你当前项目的影响

你现在的前端是 **Flask + Jinja2 模板 + 原生 JavaScript**（看 `templates/` 和 `static/` 目录），不是 SPA 框架。

**这其实是好事**——原生 JS + HTML 模板的兼容性天然就好，不像 React/Vue 打包后可能用到新特性。

### 4.3 实操建议

```javascript
// ✅ 安全使用的写法（Chrome 88+ 都支持）
const data = await fetch('/api/jobs').then(r => r.json());
const name = data?.user?.name ?? '未知';
document.querySelector('#result').innerHTML = `<p>${name}</p>`;

// ❌ 避免使用的写法
// 1. Top-level await（Chrome 89+才稳定）
// await fetch(...)  // 不要在模块顶层直接 await

// 2. structuredClone（Chrome 98+）
// const copy = structuredClone(obj)  // 用 JSON.parse(JSON.stringify(obj)) 代替

// 3. Array.at()（Chrome 92+，88不支持）
// arr.at(-1)  // 用 arr[arr.length - 1] 代替

// 4. CSS :has()（Chrome 105+）
// 不要用 :has() 选择器
```

### 4.4 如果以后要升级前端框架

之前的文档提到了 Vue3 + Element Plus。如果你未来要做前端升级：

| 框架/库 | Chrome 88 兼容？ | 说明 |
|---------|-----------------|------|
| Vue 3 | ✅ 支持 | 官方支持到 Chrome ≥64 |
| Element Plus | ✅ 支持 | 跟随 Vue 3 |
| Tailwind CSS | ✅ 支持 | 编译后是纯 CSS |
| ECharts 5 | ✅ 支持 | 兼容到 IE11 |
| Vite 构建工具 | ✅ 但需配置 | 设置 `build.target: 'chrome88'` |

> [!TIP]
> **结论：Chrome 88/109 对你来说不是大问题。**
> 你当前的纯 JS + 模板方案兼容性很好。
> 如果将来用 Vue3，也能支持。只要别用太新的 CSS 特性和 JS API 就行。

---

## 问题五：「新建项目骨架」到底是什么意思？

### 5.1 先消除误解

> **不是重新建一个全新项目，不是从零开始！**

「新建项目骨架」的意思是：

```
在现有项目旁边（或新分支上），先搭好一个干净的目录结构框架（空壳），
然后把你现有的代码，一个模块一个模块地「搬」进去。
```

就像装修房子：不是拆了重建，而是先画好新的房间布局图（骨架），然后把旧家具（现有代码）搬到对应的新房间里。

### 5.2 具体怎么操作（推荐方案）

#### 方案A：在现有项目上用 Git 分支（推荐 ✅）

```bash
# 1. 先确保当前代码已提交
git add -A && git commit -m "保存当前状态"

# 2. 创建重构分支
git checkout -b refactor/clean-skeleton

# 3. 在分支上调整目录结构
# （只是移动文件和改 import，不改业务逻辑）

# 4. 改好一个模块就测试一个模块
# 5. 全部OK后合并回主分支
```

#### 方案B：在旁边建目录，逐步迁移

```bash
# 不推荐这种方式，因为你是一个人维护，
# 同时维护两个项目目录会混乱。
```

### 5.3 你的项目其实不需要大改

看了你现在的结构，**已经相当不错了**：

```
multi-rider/
├── app.py              ← 入口，清晰
├── worker.py           ← Worker入口，清晰
├── modules/            ← 业务模块，按功能划分，很好
│   ├── detection/
│   ├── face/
│   ├── dispatch/
│   └── training/
├── shared/             ← 公共代码，合理
│   ├── config/
│   ├── db/
│   ├── inference/
│   └── utils/
├── static/             ← 前端静态文件
├── templates/          ← Jinja2 模板
├── model/              ← AI 模型文件
├── tests/              ← 测试
└── ops/                ← 部署配置
```

**你不需要像之前文档说的那样做大规模重构。** 之前的文档给出的是一个「理想化」的目录结构，适合全新项目从零搭建。你的项目已经在线上运行、有真实业务，**稳定性比「漂亮的结构」更重要**。

### 5.4 如果要优化，建议只做小幅调整

```
你可以做的小改进（可选，不紧急）：

1. detection/job_routes.py（12KB）有点大
   → 可以把业务逻辑提取到 detection/services/ 下面
   → 让 routes.py 只负责路由和参数校验

2. 给 shared/ 加一层抽象
   → 比如 shared/db/ 里加一个统一的数据库工厂方法
   → 这样切换 KingbaseV8 / Oracle 时只改一处

以上都是锦上添花，不做也完全没问题。
```

> [!IMPORTANT]
> **核心建议：不要为了重构而重构。**
> 你是一个人维护，项目已经跑起来了。把精力放在：
> 1. 完成 Ubuntu 22 部署
> 2. 把 detection 模块的 Worker 迁移完成
> 3. 准备比赛材料
>
> 这些实际产出上，比「完美的代码结构」有价值得多。

---

## 综合建议：你的优先级排序

根据你的实际情况（一人维护、准备迁移 Ubuntu、准备参赛），优先级应该是：

```
优先级1 ⭐⭐⭐⭐⭐  完成 Ubuntu 22 部署（用 systemd，不用 Docker）
优先级2 ⭐⭐⭐⭐⭐  完成 detection 模块的 Worker 迁移
优先级3 ⭐⭐⭐⭐    准备比赛材料（定位文档、案例数据、PPT）
优先级4 ⭐⭐⭐      前端页面优化（在 Chrome 88 兼容范围内做美化）
优先级5 ⭐⭐        代码结构小幅优化（detection/job_routes.py 拆分等）
优先级6 ⭐          上 Docker（等前面都稳定了再说）
```

> [!TIP]
> 项目定位文档已经为你单独写好了，见 [project_positioning.md](./project_positioning.md)
