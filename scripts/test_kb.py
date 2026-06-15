#!/usr/bin/env python3
"""
Knowledge Base (知识库/RAG) 功能测试脚本。

测试流程：
  1. 可选：删除同名旧知识库
  2. 创建知识库
  3. 上传 wcnrbhf.txt（《中华人民共和国未成年人保护法》全文）
  4. 将文件关联到知识库
  5. 等待索引完成
  6. 用 @知识库 进行 RAG 对话
  7. 清理（可选）

用法：
  python scripts/test_kb.py --api-key sk-xxx --insecure
  python scripts/test_kb.py --api-key sk-xxx --insecure --cleanup
  python scripts/test_kb.py --api-key sk-xxx --insecure --replace-existing --kb-name wcnr_qincai_law
  python scripts/test_kb.py --api-key sk-xxx --insecure --source-file 你的文档.txt

注意：此脚本仅使用 Python 标准库，无需安装第三方包。
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://10.2.164.106/v2"
DEFAULT_MODEL = "ayenaspring-pro-001"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_FILE = REPO_ROOT / "wcnrbhf.txt"
DEFAULT_KB_NAME = "wcnr_qincai_law"


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


def parse_error_body(error: HTTPError):
    raw = error.read()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw.decode("utf-8", errors="replace")}


def delete_optional(client: ApiClient, path: str, label: str) -> bool:
    try:
        status, data = client.delete(path)
        print(f"  [PASS] {label} (status={status})")
        if data:
            preview = json.dumps(data, ensure_ascii=False, indent=2)
            if len(preview) > 800:
                preview = preview[:800] + "\n  ... (截断)"
            print(f"  响应: {preview}")
        return True
    except HTTPError as e:
        data = parse_error_body(e)
        if e.code == 404:
            print(f"  [SKIP] {label}: 不存在，无需删除 (status=404)")
            return True
        print(f"  [FAIL] {label} (status={e.code})")
        if data:
            print(f"  响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return False


def main():
    parser = argparse.ArgumentParser(description="测试锐智平台知识库(KB/RAG)功能")
    parser.add_argument("--base-url", default=os.getenv("RUIZHI_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key", default=os.getenv("RUIZHI_API_KEY"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--insecure", action="store_true", help="跳过HTTPS证书验证")
    parser.add_argument("--cleanup", action="store_true", help="测试完成后删除创建的知识库和文件")
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="创建前先删除同名旧知识库，适合内网重建全文知识库",
    )
    parser.add_argument(
        "--delete-file-id",
        action="append",
        default=[],
        help="额外删除旧平台文件ID；可重复传入，用于清理上次上传但未删除的文件",
    )
    parser.add_argument(
        "--source-file",
        "--custom-file",
        dest="source_file",
        default=str(DEFAULT_SOURCE_FILE),
        help="要上传的法律全文文件，默认读取项目根目录 wcnrbhf.txt",
    )
    parser.add_argument(
        "--kb-name",
        default=os.getenv("RUIZHI_KB_NAME", DEFAULT_KB_NAME),
        help=f"知识库名称，默认读取 RUIZHI_KB_NAME 或使用 {DEFAULT_KB_NAME}",
    )
    parser.add_argument("--index-wait", type=int, default=15, help="等待索引完成的秒数（默认15）")
    args = parser.parse_args()

    if not args.api_key:
        print("错误：缺少 API Key。用 --api-key 传入或设置环境变量 RUIZHI_API_KEY", file=sys.stderr)
        return 1

    client = ApiClient(args.base_url, args.api_key, args.timeout, args.insecure)
    kb_name = args.kb_name
    file_id = None
    ok_count = 0
    fail_count = 0
    step_no = 1

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
    if args.replace_existing or args.delete_file_id:
        step(step_no, "删除旧知识库/旧文件")
        step_no += 1
        if args.replace_existing:
            if not delete_optional(client, f"/kbs/{quote(kb_name)}", f"删除同名旧知识库 {kb_name}"):
                return 1
        for old_file_id in args.delete_file_id:
            if not delete_optional(client, f"/files/{quote(old_file_id)}", f"删除旧平台文件 {old_file_id}"):
                return 1

    # ------------------------------------------------------------------
    step(step_no, "创建知识库")
    step_no += 1
    # ------------------------------------------------------------------
    print(f"  知识库名称: {kb_name}")
    try:
        status, data = client.post("/kbs", {
            "name": kb_name,
            "description": f"中华人民共和国未成年人保护法全文知识库 ({time.strftime('%Y-%m-%d %H:%M')})",
            "split_config": {
                "split_type": 1,
                "chunk_overlap_len": 80,
                "chunk_max_len": 800,
                "embedding_threshold": 0.5,
                "zh_title_enhance": True,
            },
        })
        check("创建知识库", status, data)
    except HTTPError as e:
        check("创建知识库", e.code, parse_error_body(e))
        print("  !! 知识库创建失败，后续步骤将跳过")
        return 1

    # ------------------------------------------------------------------
    step(step_no, "准备并上传文件")
    step_no += 1
    # ------------------------------------------------------------------
    file_path = Path(args.source_file)
    if not file_path.is_absolute():
        file_path = (REPO_ROOT / file_path).resolve()
    if not file_path.exists():
        print(f"  错误：文件不存在: {file_path}")
        return 1
    print(f"  使用法律全文文件: {file_path}")
    print(f"  文件大小: {file_path.stat().st_size} 字节")

    try:
        status, data = client.upload_file("/files", file_path)
        if check("上传文件", status, data):
            if isinstance(data, dict):
                file_id = data.get("id") or (data.get("data") or {}).get("id")
            print(f"  文件ID: {file_id}")
    except HTTPError as e:
        check("上传文件", e.code, parse_error_body(e))

    if not file_id:
        print("  !! 文件上传失败，无法继续")
        return 1

    # ------------------------------------------------------------------
    step(step_no, "将文件关联到知识库")
    step_no += 1
    # ------------------------------------------------------------------
    try:
        status, data = client.post(f"/kbs/{quote(kb_name)}/files", {
            "file_ids": [file_id]
        })
        check("关联文件到知识库", status, data)
    except HTTPError as e:
        check("关联文件到知识库", e.code, parse_error_body(e))

    # ------------------------------------------------------------------
    step(step_no, f"等待索引完成（{args.index_wait}秒）")
    step_no += 1
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
        check("查询知识库文件列表", e.code, parse_error_body(e))

    # ------------------------------------------------------------------
    step(step_no, "RAG 对话测试 — 用 @知识库 引用知识")
    step_no += 1
    # ------------------------------------------------------------------
    questions = [
        "根据未成年人保护法，父母或者其他监护人应当履行哪些监护职责？",
        "学校在保护未成年人方面有哪些职责？",
        "网络产品和服务提供者发现未成年人遭受网络欺凌时应当怎么处理？",
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
            check(f"RAG对话({i})", e.code, parse_error_body(e))

    # ------------------------------------------------------------------
    step(step_no, "普通对话对比（不用知识库）")
    step_no += 1
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
        check("普通对话（无RAG）", e.code, parse_error_body(e))

    # ------------------------------------------------------------------
    # 清理
    # ------------------------------------------------------------------
    if args.cleanup:
        step(step_no, "清理测试资源")
        step_no += 1

        try:
            status, data = client.delete(f"/kbs/{quote(kb_name)}/files/{quote(file_id)}")
            check("从知识库移除文件", status, data)
        except HTTPError as e:
            check("从知识库移除文件", e.code, parse_error_body(e))

        try:
            status, data = client.delete(f"/kbs/{quote(kb_name)}")
            check("删除知识库", status, data)
        except HTTPError as e:
            check("删除知识库", e.code, parse_error_body(e))

        try:
            status, data = client.delete(f"/files/{quote(file_id)}")
            check("删除文件", status, data)
        except HTTPError as e:
            check("删除文件", e.code, parse_error_body(e))
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

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
