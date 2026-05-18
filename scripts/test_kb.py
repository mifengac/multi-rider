#!/usr/bin/env python3
"""
Knowledge Base (知识库/RAG) 功能测试脚本。

测试流程：
  1. 创建知识库
  2. 创建一个测试文件（侵财相关法律知识）
  3. 上传文件到平台
  4. 将文件关联到知识库
  5. 等待索引完成
  6. 用 @知识库 进行 RAG 对话
  7. 清理（可选）

用法：
  python scripts/test_kb.py --api-key sk-xxx --insecure
  python scripts/test_kb.py --api-key sk-xxx --insecure --cleanup
  python scripts/test_kb.py --api-key sk-xxx --insecure --custom-file 你的文档.txt

注意：此脚本仅使用 Python 标准库，无需安装第三方包。
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://10.2.164.106/v2"
DEFAULT_MODEL = "ayenaspring-pro-001"

SAMPLE_CONTENT = """\
未成年人侵财犯罪法律知识摘要

一、侵财犯罪的主要类型
侵财犯罪是指以非法占有为目的，侵犯他人财产权利的犯罪行为。常见类型包括：
1. 盗窃罪：秘密窃取他人财物。未成年人盗窃案件中，入室盗窃、扒窃、商场盗窃最为常见。
2. 抢劫罪：以暴力、胁迫或其他方法抢劫公私财物。未成年人抢劫多发生在学校周边。
3. 抢夺罪：乘人不备公然夺取他人财物。
4. 诈骗罪：虚构事实或隐瞒真相骗取财物。未成年人网络诈骗案件呈上升趋势。
5. 敲诈勒索罪：以威胁或要挟方法索取财物。校园欺凌中常伴随敲诈勒索行为。

二、未成年人刑事责任年龄
根据《刑法》第十七条：
- 不满12周岁：不负刑事责任。
- 已满12周岁不满14周岁：犯故意杀人、故意伤害致人死亡或以特别残忍手段致人重伤造成严重残疾，情节恶劣，经最高人民检察院核准追诉的，应当负刑事责任。
- 已满14周岁不满16周岁：对故意杀人、故意伤害致人重伤或死亡、强奸、抢劫、贩卖毒品、放火、爆炸、投放危险物质罪负刑事责任。
- 已满16周岁：对所有犯罪负刑事责任。
- 已满14周岁不满18周岁：应当从轻或减轻处罚。不适用死刑。

三、未成年人侵财案件的处理原则
1. 教育为主、惩罚为辅原则。
2. 分级干预：训诫、责令管教、专门教育、刑事处罚。
3. 附条件不起诉：对于可能判处一年有期徒刑以下刑罚的未成年犯罪嫌疑人，检察机关可以作出附条件不起诉决定。
4. 犯罪记录封存：犯罪时不满18周岁，被判处五年以下有期徒刑的，犯罪记录予以封存。

四、盗窃罪量刑标准（侵财重点）
- 数额较大（1000-3000元以上）：三年以下有期徒刑、拘役或管制。
- 数额巨大（3万-10万元以上）：三年以上十年以下有期徒刑。
- 数额特别巨大（30万-50万元以上）：十年以上有期徒刑或无期徒刑。
- 多次盗窃、入户盗窃、携带凶器盗窃、扒窃的，不论金额均构成盗窃罪。

五、未成年人侵财犯罪的预防
1. 家庭预防：加强监护责任，关注留守儿童、困境儿童。
2. 学校预防：法治教育、心理辅导、防欺凌机制。
3. 社会预防：社区矫正、帮教基地、就业帮扶。
4. 重点区域防控：学校周边、网吧、商业区等侵财案件高发区域。
"""


class ApiClient:
    def __init__(self, base_url: str, api_key: str, timeout: int, insecure: bool):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.ctx = None
        if insecure:
            self.ctx = ssl._create_unverified_context()

    def _request(self, method, path, *, json_body=None, headers=None, body=None):
        url = self.base_url + path
        h = {"Authorization": f"Bearer {self.api_key}"}
        if headers:
            h.update(headers)
        data = body
        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            h.setdefault("Content-Type", "application/json")
        req = Request(url, data=data, headers=h, method=method)
        with urlopen(req, timeout=self.timeout, context=self.ctx) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None

    def get(self, path):
        return self._request("GET", path)

    def post(self, path, payload):
        return self._request("POST", path, json_body=payload)

    def delete(self, path):
        return self._request("DELETE", path)

    def upload_file(self, path: str, file_path: Path):
        boundary = "----kb-test-" + uuid.uuid4().hex
        parts = []
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(b'Content-Disposition: form-data; name="purpose"\r\n\r\nkbs\r\n')
        filename = file_path.name
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: text/plain\r\n\r\n".encode()
        )
        parts.append(file_path.read_bytes())
        parts.append(b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        return self._request("POST", path, headers=headers, body=body)


def step(num, title):
    print(f"\n{'='*60}")
    print(f"  步骤 {num}: {title}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="测试锐智平台知识库(KB/RAG)功能")
    parser.add_argument("--base-url", default=os.getenv("RUIZHI_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key", default=os.getenv("RUIZHI_API_KEY"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--insecure", action="store_true", help="跳过HTTPS证书验证")
    parser.add_argument("--cleanup", action="store_true", help="测试完成后删除创建的知识库和文件")
    parser.add_argument("--custom-file", default=None, help="使用自定义文件代替内置测试文本")
    parser.add_argument("--kb-name", default=None, help="知识库名称，默认自动生成")
    parser.add_argument("--index-wait", type=int, default=15, help="等待索引完成的秒数（默认15）")
    args = parser.parse_args()

    if not args.api_key:
        print("错误：缺少 API Key。用 --api-key 传入或设置环境变量 RUIZHI_API_KEY", file=sys.stderr)
        return 1

    client = ApiClient(args.base_url, args.api_key, args.timeout, args.insecure)
    kb_name = args.kb_name or f"wcnr_test_{time.strftime('%m%d_%H%M%S')}"
    file_id = None
    ok_count = 0
    fail_count = 0

    def check(label, status, data):
        nonlocal ok_count, fail_count
        success = 200 <= status < 300
        mark = "PASS" if success else "FAIL"
        if success:
            ok_count += 1
        else:
            fail_count += 1
        print(f"  [{mark}] {label} (status={status})")
        if data:
            preview = json.dumps(data, ensure_ascii=False, indent=2)
            if len(preview) > 800:
                preview = preview[:800] + "\n  ... (截断)"
            print(f"  响应: {preview}")
        return success

    # ------------------------------------------------------------------
    step(1, "创建知识库")
    # ------------------------------------------------------------------
    print(f"  知识库名称: {kb_name}")
    try:
        status, data = client.post("/kbs", {
            "name": kb_name,
            "description": f"未成年人侵财知识库 - 测试 ({time.strftime('%Y-%m-%d %H:%M')})",
            "split_config": {
                "split_type": 1,
                "chunk_overlap_len": 50,
                "chunk_max_len": 512,
                "embedding_threshold": 0.5,
                "zh_title_enhance": True,
            },
        })
        check("创建知识库", status, data)
    except HTTPError as e:
        raw = e.read()
        check("创建知识库", e.code, json.loads(raw) if raw else None)
        print("  !! 知识库创建失败，后续步骤将跳过")
        return 1

    # ------------------------------------------------------------------
    step(2, "准备并上传文件")
    # ------------------------------------------------------------------
    if args.custom_file:
        file_path = Path(args.custom_file)
        if not file_path.exists():
            print(f"  错误：文件不存在: {file_path}")
            return 1
        print(f"  使用自定义文件: {file_path}")
    else:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", prefix="wcnr_qincai_",
            delete=False, encoding="utf-8"
        )
        tmp.write(SAMPLE_CONTENT)
        tmp.close()
        file_path = Path(tmp.name)
        print(f"  使用内置测试文本，已写入: {file_path}")
        print(f"  文件大小: {file_path.stat().st_size} 字节")

    try:
        status, data = client.upload_file("/files", file_path)
        if check("上传文件", status, data):
            if isinstance(data, dict):
                file_id = data.get("id") or (data.get("data") or {}).get("id")
            print(f"  文件ID: {file_id}")
    except HTTPError as e:
        raw = e.read()
        check("上传文件", e.code, json.loads(raw) if raw else None)

    if not file_id:
        print("  !! 文件上传失败，无法继续")
        return 1

    # ------------------------------------------------------------------
    step(3, "将文件关联到知识库")
    # ------------------------------------------------------------------
    try:
        status, data = client.post(f"/kbs/{quote(kb_name)}/files", {
            "file_ids": [file_id]
        })
        check("关联文件到知识库", status, data)
    except HTTPError as e:
        raw = e.read()
        check("关联文件到知识库", e.code, json.loads(raw) if raw else None)

    # ------------------------------------------------------------------
    step(4, f"等待索引完成（{args.index_wait}秒）")
    # ------------------------------------------------------------------
    print(f"  平台需要时间对文件进行切片和向量化...")
    for i in range(args.index_wait, 0, -1):
        print(f"\r  等待中... {i}s ", end="", flush=True)
        time.sleep(1)
    print("\r  等待完成。              ")

    # 检查知识库文件状态
    try:
        status, data = client.get(f"/kbs/{quote(kb_name)}/files")
        check("查询知识库文件列表", status, data)
    except HTTPError as e:
        raw = e.read()
        check("查询知识库文件列表", e.code, json.loads(raw) if raw else None)

    # ------------------------------------------------------------------
    step(5, "RAG 对话测试 — 用 @知识库 引用知识")
    # ------------------------------------------------------------------
    questions = [
        "未成年人盗窃2000元会怎么处罚？",
        "14岁的人抢劫需要负刑事责任吗？",
        "侵财犯罪有哪些类型？",
    ]

    for i, q in enumerate(questions, 1):
        print(f"\n  --- 问题 {i}: {q} ---")
        try:
            status, data = client.post("/chat/completions", {
                "model": args.model,
                "max_tokens": 2000,
                "messages": [
                    {"role": "user", "content": q},
                    {"role": "run", "content": f"@{kb_name}"},
                ],
            })
            if check(f"RAG对话({i})", status, data):
                choices = data.get("choices", [])
                for c in choices:
                    msg = c.get("message", {})
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "assistant":
                        print(f"\n  [AI回答]:\n  {content[:500]}")
                        if len(content) > 500:
                            print("  ... (截断)")
                    elif role == "docs":
                        print(f"\n  [知识来源]: {content[:300]}")
                        if len(content) > 300:
                            print("  ... (截断)")
        except HTTPError as e:
            raw = e.read()
            check(f"RAG对话({i})", e.code, json.loads(raw) if raw else None)

    # ------------------------------------------------------------------
    step(6, "普通对话对比（不用知识库）")
    # ------------------------------------------------------------------
    q = questions[0]
    print(f"  问题: {q}")
    try:
        status, data = client.post("/chat/completions", {
            "model": args.model,
            "max_tokens": 2000,
            "messages": [
                {"role": "user", "content": q},
            ],
        })
        if check("普通对话（无RAG）", status, data):
            choices = data.get("choices", [])
            for c in choices:
                msg = c.get("message", {})
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    print(f"\n  [AI回答（无知识库）]:\n  {content[:500]}")
    except HTTPError as e:
        raw = e.read()
        check("普通对话（无RAG）", e.code, json.loads(raw) if raw else None)

    # ------------------------------------------------------------------
    # 清理
    # ------------------------------------------------------------------
    if args.cleanup:
        step(7, "清理测试资源")

        try:
            status, data = client.delete(f"/kbs/{quote(kb_name)}/files/{quote(file_id)}")
            check("从知识库移除文件", status, data)
        except HTTPError as e:
            raw = e.read()
            check("从知识库移除文件", e.code, json.loads(raw) if raw else None)

        try:
            status, data = client.delete(f"/kbs/{quote(kb_name)}")
            check("删除知识库", status, data)
        except HTTPError as e:
            raw = e.read()
            check("删除知识库", e.code, json.loads(raw) if raw else None)

        try:
            status, data = client.delete(f"/files/{quote(file_id)}")
            check("删除文件", status, data)
        except HTTPError as e:
            raw = e.read()
            check("删除文件", e.code, json.loads(raw) if raw else None)
    else:
        print(f"\n  提示：知识库 '{kb_name}' 和文件 '{file_id}' 已保留。")
        print(f"  如需清理，重新运行并加 --cleanup 参数。")
        print(f"  保留的知识库可以在后续开发中直接使用。")

    # ------------------------------------------------------------------
    # 汇总
    # ------------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"  测试完成: PASS={ok_count}, FAIL={fail_count}")
    print(f"{'='*60}")
    if fail_count == 0:
        print("\n  知识库RAG功能正常！可以用于项目。")
        print(f"\n  关键信息（开发时需要）:")
        print(f"    BASE_URL  = {args.base_url}")
        print(f"    MODEL     = {args.model}")
        print(f"    KB_NAME   = {kb_name}")
        print(f"    FILE_ID   = {file_id}")
        print(f"\n  RAG调用方式:")
        print(f'    messages = [')
        print(f'      {{"role": "user", "content": "你的问题"}},')
        print(f'      {{"role": "run", "content": "@{kb_name}"}},')
        print(f'    ]')
    else:
        print(f"\n  有 {fail_count} 项测试失败，请检查上面的错误信息。")

    # 清理临时文件
    if not args.custom_file:
        try:
            file_path.unlink()
        except OSError:
            pass

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
