# Post-Refactor Regression Checklist

> 用途：在完成目录重构后，按新的代码结构回归 detection、face、dispatch、training 四条主链路。

## Scope

- 本清单关注“重构后还能不能正常工作”。
- 本清单默认代码入口仍是 app.py，页面入口仍是首页工作台。
- 本清单不要求一次性完成所有真实内网联调；可先做本地 smoke test，再做内网联调。

## Before Start

- 确认当前启动方式仍然可用：.venv\Scripts\python.exe app.py
- 确认重点新目录存在：modules、shared、templates/modules、static/modules、ops、docs
- 确认首页仍可打开，且没有因为模板 include 路径迁移而报 500
- 确认 git status 中没有误把本地 .env、.mcp 之类环境文件加入提交范围

## Global Smoke Test

- 启动服务，确认首页可访问
- 访问首页后确认四个主页签仍可切换：数据库检测、本地上传检测、人脸、训练、下发
- 确认首页加载的脚本已来自新路径：static/modules 和 static/shared
- 确认没有明显的模板找不到、静态资源 404、Blueprint 未注册错误

## Detection

### Code Location

- 路由入口：modules/detection/job_routes.py
- 上传入口：modules/detection/upload_routes.py
- 文件下载：modules/detection/file_routes.py
- 服务层：modules/detection/services
- 模板：templates/modules/detection
- 脚本：static/modules/detection

### Local Smoke Test

- 打开首页数据库检测页签，确认页面正常渲染
- 提交一组时间范围参数，确认接口能返回任务创建结果或明确的数据库连接错误
- 打开本地上传检测页签，确认 ZIP 或视频上传表单正常显示
- 尝试上传一个小文件，确认任务能进入进度轮询
- 打开历史页，确认历史列表页和详情页模板路径已切换后仍可访问
- 检查结果下载入口是否正常生成

### Real Environment Regression

- 使用真实 Oracle 连接回归数据库检测主链路
- 确认 URL 拉取、图片下载、推理、结果清单写入完整可用
- 回归本地上传 ZIP 与视频两种路径
- 确认 output 目录下结果 ZIP 和 _results 清单结构保持兼容

## Face

### Code Location

- 路由入口：modules/face/routes.py
- 服务层：modules/face/services
- 旧流水线：modules/face/legacy
- SQL 资产：modules/face/sql
- 模板：templates/modules/face
- 脚本：static/modules/face

### Local Smoke Test

- 打开首页人脸页签，确认人脸库状态区域正常渲染
- 访问人员名录列表，确认分页和搜索接口可返回结果或明确报错
- 打开任一历史任务详情，确认结果图身份识别区域仍可展示
- 对单张或多张结果图触发识别，确认接口返回结构正常

### Real Environment Regression

- 回归人脸库同步
- 回归特征重建
- 回归单图识别和批量识别
- 确认识别结果仍能回流到 dispatch 队列
- 确认 face_library.sql 在新路径下被正确读取

## Dispatch

### Code Location

- 路由入口：modules/dispatch/routes.py
- 服务层：modules/dispatch/services
- 仓储：modules/dispatch/repository
- 模板：templates/modules/dispatch
- 脚本：static/modules/dispatch

### Local Smoke Test

- 打开首页下发页签，确认认证区、队列区、草稿区、短信区正常渲染
- 刷新队列，确认接口能返回空队列或已有队列，而不是模板或导入错误
- 选中一个队列项后，确认 payload 预览和短信预览能生成

### Real Environment Regression

- 使用真实平台账号回归认证流程
- 回归属地重查
- 回归 payload 预览
- 回归真实任务下发
- 回归短信预览和短信发送
- 确认下发记录和短信记录仍可回看

## Training

### Code Location

- 路由入口：modules/training/routes.py
- 服务层：modules/training/services
- 页面：templates/modules/training
- 脚本：static/modules/training

### Local Smoke Test

- 打开首页训练页签，确认数据集列表正常显示
- 创建一个测试数据集，确认 datasets 与 jobs.sqlite3 写入正常
- 导入一个测试 ZIP，确认图片进入数据集
- 打开数据集工作台，确认图片列表、标注区、保存标注仍可用
- 创建训练任务，确认任务列表刷新正常
- 打开训练评估页和模型管理页，确认页面模板已迁移后仍可访问

### Real Environment Regression

- 回归自动预标注任务
- 回归真实训练任务
- 回归训练评估页展示
- 回归 best.pt 发布到 model 目录
- 回归模型槽位切换和回滚

## Shared Infrastructure

### Code Location

- 配置：shared/config/config.py
- 数据库：shared/db
- 推理：shared/inference/infer_service.py
- 归属：shared/ownership/ownership.py
- 工具：shared/utils/helpers.py

### Checks

- 确认 shared/config/config.py 中 BASE_DIR 指向仓库根目录
- 确认环境变量仍能从预期位置加载
- 确认 SQLite 初始化、旧任务清理、运行中任务中断恢复逻辑不受迁移影响
- 确认 Oracle 辅助函数可被 detection 和 dispatch 复用
- 确认默认模型预热仍从 shared/inference/infer_service.py 进入

## Docs And Ops

- 确认 README 中的目录结构、Docker 构建命令、环境文件路径都已改成新结构
- 确认 ops/Dockerfile 能复制 modules、shared、templates、static 等新目录
- 确认 docs/handoff 中的交接文件与当前目录结构一致

## Expected Pass Condition

- 首页和四个业务模块页面都能打开
- 关键 API 不因为旧路径删除而报导入错误
- 真实环境下四条业务链路都能完整走通或至少给出业务级错误，而不是结构级错误
- 新同事不需要再去旧的 routes、service、db、utils 目录找代码

## If Something Fails

- 先判断是结构迁移问题还是业务环境问题
- 结构迁移问题优先检查 import、Blueprint 注册、render_template 路径、url_for 名称
- 业务环境问题优先检查 Oracle、模型文件、人脸库底库、外部平台配置