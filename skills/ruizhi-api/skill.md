---
name: ruizhi-api
description: 锐智AI服务平台 API 调用助手。当用户需要调用锐智AI平台的接口（模型、文件、知识库、向量、音频、OCR、翻译、会话等）时触发。
---

# 锐智AI服务平台 API Skill

## 平台信息

- **BASE_URL**: `https://10.2.164.106/v2`
- **API_KEY**: 从"锐智AI服务平台 -> 个人中心 -> APIKEY管理"获取
- **project**: 应用方自身的项目标识，联系锐安管理员申请
- **接口标准**: 参考 OpenAI 接口标准，细节以本文档为准
- **HTTPS**: 需忽略证书验证（curl 用 `-k`，Python 用 `httpx.Client(verify=False)` 或 `requests(..., verify=False)`）

## Python 初始化模板

```python
import openai
import httpx

API_KEY = "<your-api-key>"
BASE_URL = "https://10.2.164.106/v2"

# 方式一：openai SDK（适用于 models/files/embeddings/chat/audio）
client = openai.Client(
    api_key=API_KEY,
    base_url=BASE_URL,
    http_client=httpx.Client(verify=False)
)

# 方式二：requests（适用于 kbs/tools 等无 openai 对应的接口）
import requests, json
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
```

---

## 1. 模型（Models）

### 列表检索
```python
models = client.models.list()
# 返回: object="list", data=[{id, object, created, owned_by, description, context_length, max_input, max_output, tools}, ...]
```

### 单个检索
```python
model = client.models.retrieve("ayenaspring-pro-001")
```

---

## 2. 文件（Files）

### 上传
```python
file = client.files.create(file=open("doc.txt", "rb"), purpose="kbs")
# 返回: {id, object, bytes, created_at, filename, purpose, owner, status, status_details}
# 单文件最大 10MB
```

### 列表
```python
files = client.files.list()
```

### 信息检索
```python
file = client.files.retrieve("file-c5a6e29a8ac648ab9f5162f6b010bb3c")
```

### 删除
```python
client.files.delete("file-c5a6e29a8ac648ab9f5162f6b010bb3c")
# 返回: {deleted: true, id, object}
```

### 内容获取
```python
content = client.files.content("file-c5a6e29a8ac648ab9f5162f6b010bb3c")
# curl 示例: curl ... > output.txt
```

---

## 3. 知识库（KnowledgeBase）

> 知识库相关接口无 openai 对应方法，使用 requests 调用。中文名称需 URL 编码（`urllib.parse.quote`）。

### 创建
```python
from urllib.parse import quote
resp = requests.post(f"{BASE_URL}/kbs", headers=headers, json={
    "name": "法律知识库",
    "description": "法律知识库",
    "split_config": {
        "split_type": 1,           # 1=字数分割
        "chunk_max_len": 512,      # 1-1000
        "chunk_overlap_len": 50,   # 0-1000
        "embedding_threshold": 0.5, # 0.1-0.9
        "zh_title_enhance": true
    }
}, verify=False)
```

### 列表
```python
resp = requests.get(f"{BASE_URL}/kbs", headers=headers, verify=False)
```

### 检索
```python
resp = requests.get(f"{BASE_URL}/kbs/{quote('法律知识库')}", headers=headers, verify=False)
```

### 修改
```python
resp = requests.post(f"{BASE_URL}/kbs/{quote('法律知识库')}", headers=headers, json={
    "name": "法律知识库-modify",
    "description": "法律知识库-modify"
}, verify=False)
```

### 删除
```python
resp = requests.delete(f"{BASE_URL}/kbs/{quote('法律知识库')}", headers=headers, verify=False)
```

### 分享
```python
resp = requests.post(f"{BASE_URL}/kbs/{quote('法律知识库')}/share", headers=headers, json={
    "user_ids": ["2"],
    "action": "SHARE"  # SHARE / UNSHARE
}, verify=False)
```

### 重置（重新解析）
```python
resp = requests.post(f"{BASE_URL}/kbs/{quote('法律知识库')}/reparsing", headers=headers, json={
    "split_type": 1,
    "chunk_max_len": 600,
    "chunk_overlap_len": 0,
    "zh_title_enhance": true
}, verify=False)
```

---

## 4. 知识库关联（Association）

### 添加文件到知识库
```python
resp = requests.post(f"{BASE_URL}/kbs/{quote('法律知识库')}/files", headers=headers, json={
    "file_ids": ["file-c5a6e29a8ac648ab9f5162f6b010bb3c"],
    "callback": "http://your-host:port/callback"  # 可选回调
}, verify=False)
# 返回 202 表示任务已接受，处理速度约 2万字/分钟
# 支持格式: txt, pdf, json, epub, docx, xls, xlsx, csv, xml, md（建议 txt）
```

### 知识库文件列表
```python
resp = requests.get(f"{BASE_URL}/kbs/{quote('法律知识库')}/files", headers=headers, verify=False)
```

### 知识库文件检索
```python
resp = requests.get(
    f"{BASE_URL}/kbs/{quote('法律知识库')}/files/file-c5a6e29a8ac648ab9f5162f6b010bb3c",
    headers=headers, verify=False
)
# 返回: {file: {...}, knowledgeBase: {...}}
```

### 删除知识库文件关联
```python
resp = requests.delete(
    f"{BASE_URL}/kbs/{quote('法律知识库')}/files/file-c5a6e29a8ac648ab9f5162f6b010bb3c",
    headers=headers, verify=False
)
```

---

## 5. 向量（Embeddings）

```python
resp = client.embeddings.create(
    model="ayenaembedding-001",
    input="法律文件的测试文本",  # 长度不超过 1024
    dimensions=1024,
    encoding_format="float"
)
# 返回: data[{embedding: [float x 1024], index, object}], usage
```

---

## 6. 重排序（Rerank）

```python
resp = requests.post(f"{BASE_URL}/rerank", headers=headers, json={
    "model": "bge-reranker-base",
    "query": "什么是人工智能",
    "documents": ["AI是机器学习的分支", "人工智能是计算机科学领域", "无关文本"],
    "top_k": 3  # 可选，默认返回全部
}, verify=False)
# 返回: results[{index, relevance_score}] 按分数降序
```

---

## 7. 音频（Audio）

### TTS 文转音
```python
resp = client.audio.speech.create(
    model="ayenaaudio-001",
    input="您好，我是云网AI服务平台",
    voice="female",       # male / female
    response_format="wav",
    speed=1.0             # 0.1 - 4.0
)
# 输出音频二进制流，需写入文件
```

### ASR 音转文
```python
resp = client.audio.transcriptions.create(
    model="ayenaaudio-001",
    language="zh",  # zh / en
    file=open("speech.wav", "rb")
)
# 返回: {text: "..."}
```

### 实时 ASR（WebSocket）
```python
import asyncio, ssl, websockets, wave, json

async def realtime_asr(file_path, api_key):
    uri = "wss://10.2.164.106/v2/audio/speech/asr"
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    async with websockets.connect(uri, ssl=ssl_ctx, extra_headers={"Authorization": f"Bearer {api_key}"}) as ws:
        await ws.send(json.dumps({"command": "start"}))
        # 等待 {"signal": "server_ready", "status": "ok"}

        with wave.open(file_path, 'rb') as wf:
            data = wf.readframes(9600)
            while data:
                await ws.send(data)
                data = wf.readframes(9600)

        await ws.send(json.dumps({"command": "end"}))
        async for msg in ws:
            resp = json.loads(msg)
            if resp.get("signal") == "finished":
                return resp.get("result")

# 音频要求: 单声道 / 16k采样 / 16bit / PCM
```

### 音频翻译（英转中）
```python
resp = client.audio.translations.create(
    model="ayenaaudio-001",
    file=open("en_speech.wav", "rb")
)
# 返回: {text: "翻译后的中文"}
```

---

## 8. 工具（Tools）

### 文本翻译
```python
resp = requests.post(f"{BASE_URL}/tools/translations", headers=headers, json={
    "model": "ayenaspring-pro-001",
    "content": "我能为您提供精准的引导式解答",
    "src_lang": "",    # 空=自动检测
    "dst_lang": "en",  # ISO 639-1 编码，空=默认中文
    "situation": ""    # 场景描述，不超过10字符
}, verify=False)
# 返回: {code: 200, data: ["translated text"]}
```

### Token 核算
```python
resp = requests.post(f"{BASE_URL}/tools/tokens", headers=headers, json={
    "model": "ayenaspring-pro-001",
    "content": "待分解的内容"
}, verify=False)
# 返回: {tokens: 19}
```

### OCR（Paddle）
```python
resp = requests.post(f"{BASE_URL}/tools/ocr/paddle", headers={"Authorization": f"Bearer {API_KEY}"}, files={
    "image": open("screenshot.png", "rb")
}, data={
    "use_angle_cls": True,
    "lang": "ch",
    "det_db_thresh": 0.3,
    "det_db_box_thresh": 0.5,
    "det_db_unclip_ratio": 1.6
}, verify=False)
# 返回: {success, results[{text, confidence, bbox}], processing_time, image_size}
```

### OCR（DeepSeek）
```python
resp = requests.post(f"{BASE_URL}/tools/ocr/deepseek", headers={"Authorization": f"Bearer {API_KEY}"}, files={
    "image": open("screenshot.png", "rb")
}, data={
    "task_type": "free_ocr",   # freeocr / markdown / parsechart / locate_object
    "resolution": "base"       # tiny / small / base / large / gundam
}, verify=False)
# 返回: {success, results[{label, text, confidence, bbox}], processing_time, image_size, text, processed_text}
```

---

## 9. 会话（Chat）

### 非流式会话
```python
resp = client.chat.completions.create(
    model="ayenaspring-pro-001",
    messages=[{"role": "user", "content": "公安执法办案的流程有哪些？"}]
)
# 返回: choices[{message: {role, content}, finish_reason}], usage
```

### 流式会话
```python
stream = client.chat.completions.create(
    model="ayenaspring-pro-001",
    stream=True,
    messages=[{"role": "user", "content": "你好"}]
)
for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="")
```

### 知识库会话
```python
resp = client.chat.completions.create(
    model="ayenaspring-pro-001",
    messages=[
        {"role": "user", "content": "法律一般是怎么分类的？"},
        {"role": "run", "content": "@法律知识库"}  # @知识库ID 引用知识库
    ]
)
# 响应中 choices 会多一条 role="docs" 的引用内容
# 支持同时 @ 多个知识库
```

### 函数调用（Function Calling）
```python
resp = client.chat.completions.create(
    model="ayenaspring-pro-001",
    stream=False,  # 仅非流式支持
    tool_choice="auto",
    tools=[{
        "type": "function",
        "function": {
            "name": "get_policeoffice_list",
            "description": "根据位置提供附近派出所列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "位置信息"}
                },
                "required": ["location"]
            }
        }
    }],
    messages=[{"role": "user", "content": "距离东升科技园最近的派出所"}]
)
# 返回: finish_reason="tool_calls", message.tool_calls[{function: {name, arguments}}]
```

### 多模态会话（图片）
```python
import base64
with open("image.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

resp = client.chat.completions.create(
    model="ayenavisual-004",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            {"type": "text", "text": "识别图中的文字，直接输出。"}
        ]
    }]
)
```

### 文件会话
```python
resp = requests.post(f"{BASE_URL}/chat/files/file-c5a6e29a8ac648ab9f5162f6b010bb3c", headers=headers, json={
    "model": "ayenaspring-pro-001",
    "messages": [{"role": "user", "content": "请列举当前法律的主要分类"}]
}, verify=False)
```

---

## 常用模型名称（示例）

| 模型 | 用途 |
|------|------|
| `ayenaspring-pro-001` | 大语言模型（720亿参数） |
| `ayenaaudio-001` | 音频模型（TTS/ASR/翻译） |
| `ayenavisual-001` / `ayenavisual-004` | 视觉多模态模型 |
| `ayenaembedding-001` | 向量嵌入模型（1024维） |
| `bge-reranker-base` | 重排序模型 |

> 实际可用模型需通过 `client.models.list()` 查询当前环境激活的模型。

## 响应码参考

| 码 | 含义 |
|----|------|
| 200 | 成功 |
| 202 | 已接受（异步任务） |
| 400 | 请求错误 |
| 401 | 未授权 |
| 403 | 禁止访问 |
| 404 | 未找到 |
| 500 | 服务器内部错误 |
