# 任务下发模块开发清单

## 1. 目标

- 在项目首页新增一级 tab：`任务下发`
- 将“人脸识别”识别成功的违法人员自动流转到任务下发模块
- 支持两种处置方式：
  - 任务平台下发
  - 短信提醒
- 用户必须先完成认证，认证成功后才能执行任务平台下发
- 短信提醒支持默认号码、默认模板、人工修改和实时预览

## 2. 参考文档

- 接口文档：`C:\Users\So\Desktop\doc2026\pcsyptrwzx_v2.3.docx`
- 短信说明：`C:\Users\So\Desktop\doc2026\prompt\oracle_dxjk.md`
- 前端原型：`C:\Users\So\Desktop\project\multi-rider\design-mockup.html`

## 3. 页面与交互

### 3.1 一级模块

- 在首页导航中新增 `任务下发` tab
- 页面分为四个主区域：
  - 平台认证
  - 待下发对象
  - 任务平台下发配置
  - 短信提醒

### 3.2 平台认证

- 输入项：
  - `username`
  - `password`
- 按钮：
  - `认证并缓存 Token`
  - `刷新 Token`
- 页面状态：
  - 未认证
  - 已认证
  - token 过期
  - 认证失败
- 页面展示：
  - token 类型
  - token 剩余有效时间
  - 最近认证时间

### 3.3 待下发对象

- 数据来源：由“人脸识别”模块自动写入待下发队列
- 单条展示字段：
  - 人脸结果图缩略图
  - 姓名 `xm`
  - 证件号码 `zjhm`
  - 联系电话 `lxdh`
  - 违法行为类型
  - 来源任务 ID
  - 相似度
  - 下发状态
- 支持：
  - 单选 / 多选
  - 查看识别来源
  - 查看任务草稿
  - 批量生成下发草稿

### 3.4 任务平台下发配置

- 用户可查看或修改：
  - `zlbt`
  - `zlnr`
  - `kssj`
  - `jzsj`
  - `qssx`
  - `fksx`
  - `zlbz`
  - `ywfzr`
  - `ywfzrlxdh`
  - `xfdw`
- 页面固定展示：
  - 认证请求头示例
  - 下发 payload 预览 JSON
  - 当前选择对象数量

### 3.5 短信提醒

- 默认值：
  - 默认手机号
  - 默认短信模板
- 支持用户修改：
  - 手机号码
  - 短信模板
- 变量替换后实时展示最终发送内容
- 支持按钮：
  - `发送短信提醒`
  - `恢复默认模板`

### 3.6 审计与历史

- 展示：
  - 最近认证记录
  - 最近下发记录
  - 最近短信写库记录
  - 失败原因
- 支持按人员、任务 ID、时间筛选

## 4. 认证接口

### 4.1 接口

- 地址：`/oauth/token`
- 方法：`POST`
- 参数：
  - `client_id=jcgkpt`
  - `client_secret=123456`
  - `grant_type=password`
  - `username`
  - `password`

### 4.2 返回值

- `access_token`
- `expires_in`
- `refresh_token`
- `scope`
- `token_type`

### 4.3 开发要求

- token 本地缓存
- 下发前自动校验 token 是否过期
- 过期后允许重新认证
- 认证失败时保留待下发队列，不丢数据

## 5. 任务平台下发接口

### 5.1 接口

- 地址：`/api/WxtdjModule/receiveAndCreateRw`
- 方法：`POST`
- 请求头：
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>`
- 请求体：数组形式

### 5.2 固定值

- `rwdyid = ecfffc32c9aa4aabb75541cb23a3270f`
- `sjcsly = yfdjzldxwlxxwffzzx`

### 5.3 字段映射

从 `ywdata.t_ap_czrk_jbxx` 获取：

- `ds || '000000'` -> `sssjDm`
- `dsmc` -> `sssjMc`
- `ssxq || '000000'` -> `ssfjDm`
- `ssxqmc` -> `ssfjMc`
- `pcs` -> `zbpcsdm`
- `pcsmc` -> `zbpcsmc`
- `dz` -> `dzmc`

动态变量：

- `zjhm`
- `lxdh`
- `xm`

其他字段按接口文档组织：

- `zlbt`
- `zlnr`
- `kssj`
- `jzsj`
- `qssx`
- `fksx`
- `bsz`
- `hcdxid`
- `hcdxmc`
- `hcdxdh`
- `zlbz`
- `ywfzr`
- `ywfzrlxdh`
- `wxtid`
- `gjdq`
- `zjlx`
- `pch`
- `dzdm`
- `xfdw`

### 5.4 开发要求

- 每次下发生成唯一 `wxtid`
- 明确记录请求报文、响应报文、返回时间
- 若接口返回部分数据异常，页面要完整展示失败原因
- 若接口整体失败，待下发状态不可误改为成功

## 6. 短信提醒写库

### 6.1 写入表

- `yfgadb.dfsdl`

### 6.2 字段

- `id`
- `mobile`
- `content`
- `deadtime`
- `status`
- `eid`
- `userid`
- `password`
- `userport`

### 6.3 默认配置

- `userid = admin`
- `password = yfga8130018`
- `userport = 0006`

### 6.4 开发要求

- `eid` 关联当前业务主键或任务唯一编号
- 短信模板变量替换后写入 `content`
- 写库成功后记录短信发送流水
- 如果手机号为空，禁止直接执行短信写库

## 7. 自动流转逻辑

### 7.1 来源

- Oracle 检测
- 本地上传检测
- 人脸识别命中结果

### 7.2 触发条件

- 人脸识别命中成功
- 识别对象包含姓名、证件号
- 满足下发业务规则

### 7.3 流转结果

- 自动写入待下发队列
- 记录来源任务 ID、来源结果图、违法行为类型、识别相似度
- 初始状态为：
  - `待认证`
  - 或 `待补充信息`

## 8. 后端建议拆分

- `routes/dispatch_routes.py`
- `service/dispatch_auth_service.py`
- `service/dispatch_task_service.py`
- `service/dispatch_sms_service.py`
- `service/dispatch_queue_service.py`

## 9. 数据表建议

建议新增 SQLite 表：

- `dispatch_auth_sessions`
- `dispatch_queue`
- `dispatch_records`
- `dispatch_sms_records`

建议字段覆盖：

- 主键 ID
- source_job_id
- source_result_id
- person_name
- person_id_no
- person_phone
- illegal_type
- similarity_score
- auth_status
- dispatch_status
- sms_status
- request_payload
- response_payload
- error_message
- created_at
- updated_at

## 10. 联调与测试

### 10.1 当前限制

- 互联网环境无法直接联调省厅接口
- 实际接口仅能在内网验证

### 10.2 本地可先做

- 认证参数组装
- token 缓存逻辑
- 下发 payload 组装
- 短信模板变量替换
- 短信写库 SQL 生成
- 审计日志与页面状态流转

### 10.3 建议联调模式

- 增加“模拟模式 / mock mode”
- mock mode 下：
  - 不真正访问认证接口
  - 不真正访问任务平台接口
  - 可把 payload 保存到本地日志
  - 可把短信 SQL 保存到本地日志

## 11. 开发顺序

1. 完成前端页面与交互
2. 完成认证接口封装与 token 缓存
3. 完成待下发队列与自动流转
4. 完成任务平台 payload 组装与下发
5. 完成短信模板预览与短信写库
6. 完成审计日志和历史记录
7. 增加 mock mode
8. 在内网完成真实联调

## 12. 验收标准

- 能在页面完成认证并看到 token 状态
- 人脸识别命中结果能自动进入待下发队列
- 用户可多选对象生成任务平台下发草稿
- 页面能正确展示字段映射和 payload 预览
- 用户修改短信模板后可实时看到最终内容
- 平台下发和短信提醒均有完整审计记录
- mock mode 下可完整走通前后端流程
