#!/usr/bin/env python3
"""
Ruizhi internal AI API smoke tester.

Usage examples:

  # PowerShell
  $env:RUIZHI_API_KEY="sk-..."
  python .\test_ruizhi_api.py --insecure

  # Test optional file/image/audio endpoints
  python .\test_ruizhi_api.py --insecure --sample-file .\sample.txt --sample-image .\sample.png --sample-wav .\zh.wav

  # Use command line key instead of environment variable
  python .\0518_test_ruizhi_api.py --api-key sk-1cac5cc6772740ceb7bf1abf75f849a9uxz5y6nlvyj9zcs9 --base-url https://10.2.164.106/v2 --insecure

The script uses only Python standard library modules, so it can run on a clean
intranet machine without installing requests/openai.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import ssl
import sys
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://10.2.164.106/v2"
DEFAULT_TEXT_MODEL = "ayenaspring-pro-001"
DEFAULT_EMBEDDING_MODEL = "ayenaembedding-001"
DEFAULT_AUDIO_MODEL = "ayenaaudio-001"
DEFAULT_VISION_MODEL = "ayenavisual-004"
DEFAULT_RERANK_MODEL = "bge-reranker-base"


@dataclass
class TestResult:
    name: str
    ok: bool
    status: int | None = None
    elapsed_ms: int | None = None
    detail: str = ""
    response_preview: Any = None
    error: str | None = None


@dataclass
class Context:
    models: list[dict[str, Any]] = field(default_factory=list)
    text_model: str = DEFAULT_TEXT_MODEL
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    audio_model: str = DEFAULT_AUDIO_MODEL
    vision_model: str = DEFAULT_VISION_MODEL
    rerank_model: str = DEFAULT_RERANK_MODEL
    uploaded_file_id: str | None = None
    kb_id: str | None = None


class ApiClient:
    def __init__(self, base_url: str, api_key: str, timeout: int, insecure: bool) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.ssl_context = None
        if insecure:
            self.ssl_context = ssl._create_unverified_context()

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        stream_preview: bool = False,
    ) -> tuple[int, dict[str, str], bytes]:
        url = self.base_url + path
        req_headers = {"Authorization": f"Bearer {self.api_key}"}
        if headers:
            req_headers.update(headers)

        data = body
        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/json")

        req = Request(url, data=data, headers=req_headers, method=method)
        with urlopen(req, timeout=self.timeout, context=self.ssl_context) as resp:
            if stream_preview:
                chunks: list[bytes] = []
                for _ in range(8):
                    line = resp.readline()
                    if not line:
                        break
                    chunks.append(line)
                    if sum(len(x) for x in chunks) > 4096:
                        break
                raw = b"".join(chunks)
            else:
                raw = resp.read()
            return resp.status, dict(resp.headers), raw

    def get_json(self, path: str) -> tuple[int, Any, bytes]:
        status, _, raw = self.request("GET", path)
        return status, parse_json(raw), raw

    def post_json(self, path: str, payload: Any) -> tuple[int, Any, bytes]:
        status, _, raw = self.request("POST", path, json_body=payload)
        return status, parse_json(raw), raw

    def delete_json(self, path: str) -> tuple[int, Any, bytes]:
        status, _, raw = self.request("DELETE", path)
        return status, parse_json(raw), raw

    def post_multipart(
        self,
        path: str,
        fields: dict[str, str | int | float | bool],
        files: dict[str, Path],
    ) -> tuple[int, Any, bytes]:
        boundary = "----ruizhi-smoke-" + uuid.uuid4().hex
        body = build_multipart_body(boundary, fields, files)
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        status, _, raw = self.request("POST", path, headers=headers, body=body)
        return status, parse_json(raw), raw


def parse_json(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def build_multipart_body(
    boundary: str,
    fields: dict[str, str | int | float | bool],
    files: dict[str, Path],
) -> bytes:
    parts: list[bytes] = []

    for name, value in fields.items():
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        if isinstance(value, bool):
            text = "true" if value else "false"
        else:
            text = str(value)
        parts.append(text.encode("utf-8"))
        parts.append(b"\r\n")

    for name, path in files.items():
        filename = path.name
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(
            (
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("utf-8")
        )
        parts.append(path.read_bytes())
        parts.append(b"\r\n")

    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts)


def preview(value: Any, limit: int = 600) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    elif isinstance(value, bytes):
        text = value[:limit].decode("utf-8", errors="replace")
    else:
        text = str(value)
    return text if len(text) <= limit else text[:limit] + "...<truncated>"


def choose_model(models: list[dict[str, Any]], fallback: str, include: list[str], exclude: list[str]) -> str:
    ids = [str(m.get("id", "")) for m in models if m.get("id")]
    for model_id in ids:
        low = model_id.lower()
        if all(word in low for word in include) and not any(word in low for word in exclude):
            return model_id
    return fallback


def run_test(name: str, func, results: list[TestResult], verbose: bool) -> None:
    started = time.perf_counter()
    try:
        status, parsed, raw, detail = func()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        ok = 200 <= int(status) < 300
        result = TestResult(
            name=name,
            ok=ok,
            status=int(status),
            elapsed_ms=elapsed_ms,
            detail=detail,
            response_preview=preview(parsed if parsed is not None else raw),
        )
    except HTTPError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        raw = exc.read()
        parsed = parse_json(raw)
        result = TestResult(
            name=name,
            ok=False,
            status=exc.code,
            elapsed_ms=elapsed_ms,
            detail="HTTP error",
            response_preview=preview(parsed if parsed is not None else raw),
            error=str(exc),
        )
    except (URLError, TimeoutError, OSError) as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        result = TestResult(
            name=name,
            ok=False,
            elapsed_ms=elapsed_ms,
            detail="Network or local IO error",
            error=str(exc),
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        result = TestResult(
            name=name,
            ok=False,
            elapsed_ms=elapsed_ms,
            detail="Unexpected error",
            error=str(exc),
            response_preview=traceback.format_exc() if verbose else None,
        )

    results.append(result)
    mark = "PASS" if result.ok else "FAIL"
    status = result.status if result.status is not None else "-"
    print(f"[{mark}] {name:<32} status={status} elapsed={result.elapsed_ms}ms {result.detail}")
    if verbose and (result.error or result.response_preview):
        if result.error:
            print(f"       error: {result.error}")
        if result.response_preview:
            print(f"       preview: {result.response_preview}")


def test_models(client: ApiClient, ctx: Context, args: argparse.Namespace):
    def _inner():
        status, parsed, raw = client.get_json("/models")
        data = parsed.get("data", []) if isinstance(parsed, dict) else []
        ctx.models = data if isinstance(data, list) else []
        if args.text_model:
            ctx.text_model = args.text_model
        else:
            ctx.text_model = choose_model(ctx.models, DEFAULT_TEXT_MODEL, ["spring"], ["embedding", "audio", "visual"])
        if args.embedding_model:
            ctx.embedding_model = args.embedding_model
        else:
            ctx.embedding_model = choose_model(ctx.models, DEFAULT_EMBEDDING_MODEL, ["embedding"], [])
        if args.audio_model:
            ctx.audio_model = args.audio_model
        else:
            ctx.audio_model = choose_model(ctx.models, DEFAULT_AUDIO_MODEL, ["audio"], [])
        if args.vision_model:
            ctx.vision_model = args.vision_model
        else:
            ctx.vision_model = choose_model(ctx.models, DEFAULT_VISION_MODEL, ["visual"], [])
        if args.rerank_model:
            ctx.rerank_model = args.rerank_model
        detail = f"models={len(ctx.models)} text_model={ctx.text_model}"
        return status, parsed, raw, detail

    return _inner


def test_model_retrieve(client: ApiClient, ctx: Context):
    def _inner():
        status, parsed, raw = client.get_json(f"/models/{quote(ctx.text_model)}")
        return status, parsed, raw, f"model={ctx.text_model}"

    return _inner


def test_chat(client: ApiClient, ctx: Context):
    def _inner():
        payload = {
            "model": ctx.text_model,
            "stream": False,
            "messages": [
                {"role": "user", "content": "请只回答两个字：正常"}
            ],
            "max_tokens": 32,
        }
        status, parsed, raw = client.post_json("/chat/completions", payload)
        return status, parsed, raw, f"model={ctx.text_model}"

    return _inner


def test_chat_stream(client: ApiClient, ctx: Context):
    def _inner():
        payload = {
            "model": ctx.text_model,
            "stream": True,
            "messages": [
                {"role": "user", "content": "请用一句话回答：接口连通。"}
            ],
            "max_tokens": 64,
        }
        status, _, raw = client.request("POST", "/chat/completions", json_body=payload, stream_preview=True)
        return status, None, raw, f"model={ctx.text_model}; read first stream chunks"

    return _inner


def test_tool_call(client: ApiClient, ctx: Context):
    def _inner():
        payload = {
            "model": ctx.text_model,
            "stream": False,
            "tool_choice": "auto",
            "messages": [
                {"role": "user", "content": "查询东升科技园附近派出所。"}
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_policeoffice_list",
                        "description": "根据当前位置，提供附近派出所位置列表，并按距离由近及远排序",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string", "description": "位置信息"}
                            },
                            "required": ["location"],
                        },
                    },
                }
            ],
        }
        status, parsed, raw = client.post_json("/chat/completions", payload)
        return status, parsed, raw, "expects finish_reason=tool_calls if supported"

    return _inner


def test_embeddings(client: ApiClient, ctx: Context):
    def _inner():
        payload = {
            "model": ctx.embedding_model,
            "input": "法律文件的测试文本",
            "dimensions": 1024,
            "encoding_format": "float",
        }
        status, parsed, raw = client.post_json("/embeddings", payload)
        return status, parsed, raw, f"model={ctx.embedding_model}"

    return _inner


def test_rerank(client: ApiClient, ctx: Context):
    def _inner():
        payload = {
            "model": ctx.rerank_model,
            "query": "什么是人工智能？",
            "documents": [
                "AI是机器学习的分支",
                "人工智能是计算机科学领域",
                "窗前明月光，疑是地上霜",
                "c++是最好的编程语言",
            ],
            "top_k": 3,
        }
        status, parsed, raw = client.post_json("/rerank", payload)
        return status, parsed, raw, f"model={ctx.rerank_model}"

    return _inner


def test_tokens(client: ApiClient, ctx: Context):
    def _inner():
        payload = {
            "model": ctx.text_model,
            "content": "我能为您提供精准的引导式解答，并在必要时引用实例作为参考",
        }
        status, parsed, raw = client.post_json("/tools/tokens", payload)
        return status, parsed, raw, f"model={ctx.text_model}"

    return _inner


def test_translation(client: ApiClient, ctx: Context):
    def _inner():
        payload = {
            "model": ctx.text_model,
            "content": "我能为您提供精准的引导式解答，并在必要时引用实例作为参考",
            "dst_lang": "en",
        }
        status, parsed, raw = client.post_json("/tools/translations", payload)
        return status, parsed, raw, f"model={ctx.text_model}"

    return _inner


def test_tts(client: ApiClient, ctx: Context, out_dir: Path):
    def _inner():
        payload = {
            "model": ctx.audio_model,
            "response_format": "wav",
            "input": "接口测试成功。",
            "voice": "female",
            "speed": 1.0,
        }
        status, _, raw = client.request("POST", "/audio/speech", json_body=payload)
        out_path = out_dir / "tts_test.wav"
        out_path.write_bytes(raw)
        return status, {"bytes": len(raw), "output": str(out_path)}, raw[:80], f"model={ctx.audio_model}; saved={out_path}"

    return _inner


def test_file_upload(client: ApiClient, ctx: Context, path: Path):
    def _inner():
        status, parsed, raw = client.post_multipart("/files", {"purpose": "kbs"}, {"file": path})
        if isinstance(parsed, dict):
            ctx.uploaded_file_id = parsed.get("id") or parsed.get("data", {}).get("id")
        return status, parsed, raw, f"file={path.name}; file_id={ctx.uploaded_file_id}"

    return _inner


def test_file_list(client: ApiClient):
    def _inner():
        status, parsed, raw = client.get_json("/files")
        return status, parsed, raw, "list current user's files"

    return _inner


def test_file_retrieve(client: ApiClient, ctx: Context):
    def _inner():
        if not ctx.uploaded_file_id:
            raise RuntimeError("No uploaded file_id; run file_upload first")
        status, parsed, raw = client.get_json(f"/files/{quote(ctx.uploaded_file_id)}")
        return status, parsed, raw, f"file_id={ctx.uploaded_file_id}"

    return _inner


def test_file_content(client: ApiClient, ctx: Context, out_dir: Path):
    def _inner():
        if not ctx.uploaded_file_id:
            raise RuntimeError("No uploaded file_id; run file_upload first")
        status, _, raw = client.request("GET", f"/files/{quote(ctx.uploaded_file_id)}/content")
        out_path = out_dir / f"download_{ctx.uploaded_file_id}.bin"
        out_path.write_bytes(raw)
        parsed = {"bytes": len(raw), "output": str(out_path)}
        return status, parsed, raw[:80], f"file_id={ctx.uploaded_file_id}; saved={out_path}"

    return _inner


def test_chat_file(client: ApiClient, ctx: Context):
    def _inner():
        if not ctx.uploaded_file_id:
            raise RuntimeError("No uploaded file_id; run file_upload first")
        payload = {
            "model": ctx.text_model,
            "messages": [
                {"role": "user", "content": "请用一句话概括这个文件的内容。"}
            ],
            "stream": False,
        }
        status, parsed, raw = client.post_json(f"/chat/files/{quote(ctx.uploaded_file_id)}", payload)
        return status, parsed, raw, f"file_id={ctx.uploaded_file_id}"

    return _inner


def test_file_delete(client: ApiClient, ctx: Context):
    def _inner():
        if not ctx.uploaded_file_id:
            raise RuntimeError("No uploaded file_id; run file_upload first")
        status, parsed, raw = client.delete_json(f"/files/{quote(ctx.uploaded_file_id)}")
        return status, parsed, raw, f"deleted test file_id={ctx.uploaded_file_id}"

    return _inner


def test_kb_create(client: ApiClient, ctx: Context):
    def _inner():
        ctx.kb_id = "api_test_" + time.strftime("%Y%m%d_%H%M%S")
        payload = {
            "name": ctx.kb_id,
            "description": "API smoke test knowledge base",
            "split_config": {
                "split_type": 1,
                "chunk_overlap_len": 50,
                "chunk_max_len": 512,
                "embedding_threshold": 0.5,
                "zh_title_enhance": True,
            },
        }
        status, parsed, raw = client.post_json("/kbs", payload)
        return status, parsed, raw, f"kbs_id={ctx.kb_id}"

    return _inner


def test_kb_list(client: ApiClient):
    def _inner():
        status, parsed, raw = client.get_json("/kbs")
        return status, parsed, raw, "list knowledge bases"

    return _inner


def test_kb_retrieve(client: ApiClient, ctx: Context):
    def _inner():
        if not ctx.kb_id:
            raise RuntimeError("Need kb_id")
        status, parsed, raw = client.get_json(f"/kbs/{quote(ctx.kb_id)}")
        return status, parsed, raw, f"kbs_id={ctx.kb_id}"

    return _inner


def test_kb_modify(client: ApiClient, ctx: Context):
    def _inner():
        if not ctx.kb_id:
            raise RuntimeError("Need kb_id")
        payload = {
            "name": ctx.kb_id,
            "description": "API smoke test knowledge base - modified",
        }
        status, parsed, raw = client.post_json(f"/kbs/{quote(ctx.kb_id)}", payload)
        return status, parsed, raw, f"kbs_id={ctx.kb_id}"

    return _inner


def test_kb_add_file(client: ApiClient, ctx: Context):
    def _inner():
        if not ctx.kb_id or not ctx.uploaded_file_id:
            raise RuntimeError("Need kb_id and uploaded_file_id")
        payload = {"file_ids": [ctx.uploaded_file_id]}
        status, parsed, raw = client.post_json(f"/kbs/{quote(ctx.kb_id)}/files", payload)
        return status, parsed, raw, f"kbs_id={ctx.kb_id}; file_id={ctx.uploaded_file_id}"

    return _inner


def test_kb_files(client: ApiClient, ctx: Context):
    def _inner():
        if not ctx.kb_id:
            raise RuntimeError("Need kb_id")
        status, parsed, raw = client.get_json(f"/kbs/{quote(ctx.kb_id)}/files")
        return status, parsed, raw, f"kbs_id={ctx.kb_id}"

    return _inner


def test_kb_file_retrieve(client: ApiClient, ctx: Context):
    def _inner():
        if not ctx.kb_id or not ctx.uploaded_file_id:
            raise RuntimeError("Need kb_id and uploaded_file_id")
        path = f"/kbs/{quote(ctx.kb_id)}/files/{quote(ctx.uploaded_file_id)}"
        status, parsed, raw = client.get_json(path)
        return status, parsed, raw, f"kbs_id={ctx.kb_id}; file_id={ctx.uploaded_file_id}"

    return _inner


def test_kb_reparsing(client: ApiClient, ctx: Context):
    def _inner():
        if not ctx.kb_id:
            raise RuntimeError("Need kb_id")
        payload = {
            "split_type": 1,
            "chunk_overlap_len": 0,
            "chunk_max_len": 600,
            "zh_title_enhance": True,
        }
        status, parsed, raw = client.post_json(f"/kbs/{quote(ctx.kb_id)}/reparsing", payload)
        return status, parsed, raw, f"kbs_id={ctx.kb_id}"

    return _inner


def test_kb_share(client: ApiClient, ctx: Context, user_id: str):
    def _inner():
        if not ctx.kb_id:
            raise RuntimeError("Need kb_id")
        payload = {"user_ids": [user_id]}
        status, parsed, raw = client.post_json(f"/kbs/{quote(ctx.kb_id)}/share", payload)
        return status, parsed, raw, f"kbs_id={ctx.kb_id}; user_id={user_id}"

    return _inner


def test_kb_remove_file(client: ApiClient, ctx: Context):
    def _inner():
        if not ctx.kb_id or not ctx.uploaded_file_id:
            raise RuntimeError("Need kb_id and uploaded_file_id")
        path = f"/kbs/{quote(ctx.kb_id)}/files/{quote(ctx.uploaded_file_id)}"
        status, parsed, raw = client.delete_json(path)
        return status, parsed, raw, f"kbs_id={ctx.kb_id}; file_id={ctx.uploaded_file_id}"

    return _inner


def test_kb_delete(client: ApiClient, ctx: Context):
    def _inner():
        if not ctx.kb_id:
            raise RuntimeError("Need kb_id")
        status, parsed, raw = client.delete_json(f"/kbs/{quote(ctx.kb_id)}")
        return status, parsed, raw, f"deleted test kbs_id={ctx.kb_id}"

    return _inner


def test_ocr_paddle(client: ApiClient, path: Path):
    def _inner():
        fields = {
            "use_angle_cls": True,
            "lang": "ch",
            "det_db_thresh": 0.3,
            "det_db_box_thresh": 0.5,
            "det_db_unclip_ratio": 1.6,
        }
        status, parsed, raw = client.post_multipart("/tools/ocr/paddle", fields, {"image": path})
        return status, parsed, raw, f"image={path.name}"

    return _inner


def test_ocr_deepseek(client: ApiClient, path: Path):
    def _inner():
        fields = {"task_type": "free_ocr", "resolution": "base"}
        status, parsed, raw = client.post_multipart("/tools/ocr/deepseek", fields, {"image": path})
        return status, parsed, raw, f"image={path.name}"

    return _inner


def test_multimodal(client: ApiClient, ctx: Context, path: Path):
    def _inner():
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        payload = {
            "model": ctx.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
                        {"type": "text", "text": "请简要描述图片内容。"},
                    ],
                }
            ],
            "stream": False,
        }
        status, parsed, raw = client.post_json("/chat/completions", payload)
        return status, parsed, raw, f"model={ctx.vision_model}; image={path.name}"

    return _inner


def test_audio_transcription(client: ApiClient, ctx: Context, path: Path):
    def _inner():
        fields = {"model": ctx.audio_model, "language": "zh"}
        status, parsed, raw = client.post_multipart("/audio/transcriptions", fields, {"file": path})
        return status, parsed, raw, f"model={ctx.audio_model}; audio={path.name}"

    return _inner


def test_audio_translation(client: ApiClient, ctx: Context, path: Path):
    def _inner():
        fields = {"model": ctx.audio_model}
        status, parsed, raw = client.post_multipart("/audio/translations", fields, {"file": path})
        return status, parsed, raw, f"model={ctx.audio_model}; audio={path.name}"

    return _inner


def validate_existing_file(value: str | None, label: str) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if not path.exists() or not path.is_file():
        raise SystemExit(f"{label} does not exist or is not a file: {path}")
    return path


def write_report(path: Path, args: argparse.Namespace, ctx: Context, results: list[TestResult]) -> None:
    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "base_url": args.base_url,
        "models_seen": len(ctx.models),
        "selected_models": {
            "text_model": ctx.text_model,
            "embedding_model": ctx.embedding_model,
            "audio_model": ctx.audio_model,
            "vision_model": ctx.vision_model,
            "rerank_model": ctx.rerank_model,
        },
        "results": [r.__dict__ for r in results],
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test Ruizhi internal AI API endpoints.")
    parser.add_argument("--base-url", default=os.getenv("RUIZHI_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key", default=os.getenv("RUIZHI_API_KEY"))
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--insecure", action="store_true", help="Disable HTTPS certificate verification.")
    parser.add_argument("--out-dir", default="ruizhi_api_test_out")
    parser.add_argument("--report", default=None, help="JSON report path. Defaults to <out-dir>/report.json.")
    parser.add_argument("--verbose", action="store_true")

    parser.add_argument("--text-model", default=None)
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument("--audio-model", default=None)
    parser.add_argument("--vision-model", default=None)
    parser.add_argument("--rerank-model", default=None)

    parser.add_argument("--sample-file", default=None, help="Optional local text/doc file for /files and /chat/files tests.")
    parser.add_argument("--sample-image", default=None, help="Optional local image for OCR and multimodal tests.")
    parser.add_argument("--sample-wav", default=None, help="Optional Chinese wav audio for transcription test.")
    parser.add_argument("--sample-en-wav", default=None, help="Optional English wav audio for audio translation test.")
    parser.add_argument("--include-kb", action="store_true", help="Create a temporary KB and add --sample-file to it.")
    parser.add_argument("--share-user-id", default=None, help="Optional user id for testing KB share on the temporary KB.")
    parser.add_argument("--cleanup", action="store_true", help="Delete file/KB resources created by this script.")
    parser.add_argument(
        "--tests",
        default="",
        help=(
            "Comma-separated test names to run. Empty means default safe tests. "
            "Names: models,model_retrieve,chat,chat_stream,tool_call,embeddings,rerank,"
            "tokens,translation,tts,file_upload,file_list,file_retrieve,file_content,chat_file,"
            "file_delete,kb_create,kb_list,kb_retrieve,kb_modify,kb_add_file,kb_files,"
            "kb_file_retrieve,kb_reparsing,kb_share,kb_remove_file,kb_delete,ocr_paddle,"
            "ocr_deepseek,multimodal,audio_transcription,audio_translation"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.api_key:
        print("Missing API key. Set RUIZHI_API_KEY or pass --api-key.", file=sys.stderr)
        return 2

    sample_file = validate_existing_file(args.sample_file, "--sample-file")
    sample_image = validate_existing_file(args.sample_image, "--sample-image")
    sample_wav = validate_existing_file(args.sample_wav, "--sample-wav")
    sample_en_wav = validate_existing_file(args.sample_en_wav, "--sample-en-wav")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = Path(args.report) if args.report else out_dir / "report.json"

    client = ApiClient(args.base_url, args.api_key, args.timeout, args.insecure)
    ctx = Context()
    results: list[TestResult] = []

    default_tests = [
        "models",
        "model_retrieve",
        "chat",
        "chat_stream",
        "tool_call",
        "embeddings",
        "rerank",
        "tokens",
        "translation",
        "tts",
    ]

    selected = [x.strip() for x in args.tests.split(",") if x.strip()] or default_tests[:]
    if sample_file:
        selected += ["file_upload", "file_list", "file_retrieve", "file_content", "chat_file"]
        if args.include_kb:
            selected += [
                "kb_create",
                "kb_list",
                "kb_retrieve",
                "kb_modify",
                "kb_add_file",
                "kb_files",
                "kb_file_retrieve",
                "kb_reparsing",
            ]
            if args.share_user_id:
                selected += ["kb_share"]
        if args.cleanup:
            if args.include_kb:
                selected += ["kb_remove_file", "kb_delete"]
            selected += ["file_delete"]
    if sample_image:
        selected += ["ocr_paddle", "ocr_deepseek", "multimodal"]
    if sample_wav:
        selected += ["audio_transcription"]
    if sample_en_wav:
        selected += ["audio_translation"]

    ordered_unique: list[str] = []
    for name in selected:
        if name not in ordered_unique:
            ordered_unique.append(name)

    tests = {
        "models": test_models(client, ctx, args),
        "model_retrieve": test_model_retrieve(client, ctx),
        "chat": test_chat(client, ctx),
        "chat_stream": test_chat_stream(client, ctx),
        "tool_call": test_tool_call(client, ctx),
        "embeddings": test_embeddings(client, ctx),
        "rerank": test_rerank(client, ctx),
        "tokens": test_tokens(client, ctx),
        "translation": test_translation(client, ctx),
        "tts": test_tts(client, ctx, out_dir),
        "file_list": test_file_list(client),
    }

    if sample_file:
        tests.update(
            {
                "file_upload": test_file_upload(client, ctx, sample_file),
                "file_retrieve": test_file_retrieve(client, ctx),
                "file_content": test_file_content(client, ctx, out_dir),
                "chat_file": test_chat_file(client, ctx),
                "file_delete": test_file_delete(client, ctx),
                "kb_create": test_kb_create(client, ctx),
                "kb_list": test_kb_list(client),
                "kb_retrieve": test_kb_retrieve(client, ctx),
                "kb_modify": test_kb_modify(client, ctx),
                "kb_add_file": test_kb_add_file(client, ctx),
                "kb_files": test_kb_files(client, ctx),
                "kb_file_retrieve": test_kb_file_retrieve(client, ctx),
                "kb_reparsing": test_kb_reparsing(client, ctx),
                "kb_remove_file": test_kb_remove_file(client, ctx),
                "kb_delete": test_kb_delete(client, ctx),
            }
        )
        if args.share_user_id:
            tests["kb_share"] = test_kb_share(client, ctx, args.share_user_id)
    if sample_image:
        tests.update(
            {
                "ocr_paddle": test_ocr_paddle(client, sample_image),
                "ocr_deepseek": test_ocr_deepseek(client, sample_image),
                "multimodal": test_multimodal(client, ctx, sample_image),
            }
        )
    if sample_wav:
        tests["audio_transcription"] = test_audio_transcription(client, ctx, sample_wav)
    if sample_en_wav:
        tests["audio_translation"] = test_audio_translation(client, ctx, sample_en_wav)

    print(f"Base URL: {args.base_url}")
    print(f"Output dir: {out_dir}")
    print(f"Tests: {', '.join(ordered_unique)}")
    print("")

    for name in ordered_unique:
        func = tests.get(name)
        if not func:
            results.append(TestResult(name=name, ok=False, detail="Unknown or missing prerequisite for test"))
            print(f"[SKIP] {name:<32} missing prerequisite or unknown test")
            continue
        run_test(name, func, results, args.verbose)

    write_report(report_path, args, ctx, results)

    passed = sum(1 for r in results if r.ok)
    failed = sum(1 for r in results if not r.ok)
    print("")
    print(f"Summary: passed={passed}, failed={failed}, report={report_path}")
    if failed:
        print("Failed tests:")
        for r in results:
            if not r.ok:
                status = r.status if r.status is not None else "-"
                print(f"  - {r.name}: status={status}, detail={r.detail}, error={r.error or ''}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
