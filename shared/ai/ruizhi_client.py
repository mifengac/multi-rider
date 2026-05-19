import json
import time
from collections.abc import Generator, Iterable
from typing import Any

import httpx

from shared.config.config import (
    RUIZHI_API_KEY,
    RUIZHI_BASE_URL,
    RUIZHI_EMBEDDING_MODEL,
    RUIZHI_RERANK_MODEL,
    RUIZHI_TEXT_MODEL,
)


_TRANSIENT_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}
_MAX_RETRIES = 2


class RuizhiApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, response_text: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class _RuizhiClient:
    def __init__(self) -> None:
        headers = {
            "Content-Type": "application/json",
            # The RuiZhi intranet gateway will negotiate zstd if offered, but
            # zstd decoding in httpx depends on an optional `zstandard` extra
            # that we do not pin. Restrict to codecs httpx always decodes
            # natively so responses (and SSE streams) never come back as
            # undecodable zstd. See docs/0519_debug.md.
            "Accept-Encoding": "gzip, deflate",
        }
        if RUIZHI_API_KEY:
            headers["Authorization"] = f"Bearer {RUIZHI_API_KEY}"
        self._client = httpx.Client(
            base_url=RUIZHI_BASE_URL.rstrip("/"),
            headers=headers,
            timeout=httpx.Timeout(60.0, read=300.0),
            verify=False,
        )

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = self._client.request(method, path, **kwargs)
                if response.status_code in _TRANSIENT_STATUS_CODES and attempt < _MAX_RETRIES:
                    self._sleep(attempt)
                    continue
                self._raise_for_status(response)
                return response.json()
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                if attempt >= _MAX_RETRIES:
                    raise RuizhiApiError(f"Ruizhi API request failed: {exc}") from exc
                self._sleep(attempt)
            except httpx.HTTPError as exc:
                raise RuizhiApiError(f"Ruizhi API request failed: {exc}") from exc

        raise RuizhiApiError("Ruizhi API request failed after retries")

    def stream(self, path: str, json_payload: dict[str, Any]) -> Generator[dict[str, Any], None, None]:
        yielded = False
        for attempt in range(_MAX_RETRIES + 1):
            try:
                with self._client.stream("POST", path, json=json_payload) as response:
                    if response.status_code in _TRANSIENT_STATUS_CODES and attempt < _MAX_RETRIES:
                        self._sleep(attempt)
                        continue
                    self._raise_for_status(response)
                    for chunk in self._iter_sse_chunks(response.iter_lines()):
                        yielded = True
                        yield chunk
                    return
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                if yielded or attempt >= _MAX_RETRIES:
                    raise RuizhiApiError(f"Ruizhi API stream failed: {exc}") from exc
                self._sleep(attempt)
            except httpx.HTTPError as exc:
                raise RuizhiApiError(f"Ruizhi API stream failed: {exc}") from exc

    @staticmethod
    def _iter_sse_chunks(lines: Iterable[str]) -> Generator[dict[str, Any], None, None]:
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            if line == "[DONE]":
                return
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuizhiApiError(f"Invalid Ruizhi stream chunk: {line}") from exc
            if isinstance(chunk, dict):
                yield chunk

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.is_success:
            return
        response.read()
        detail = _response_error_detail(response)
        raise RuizhiApiError(
            f"Ruizhi API returned HTTP {response.status_code}: {detail}",
            status_code=response.status_code,
            response_text=response.text,
        )

    @staticmethod
    def _sleep(attempt: int) -> None:
        time.sleep(0.5 * (2**attempt))


_client: _RuizhiClient | None = None


def _get_client() -> _RuizhiClient:
    global _client
    if _client is None:
        _client = _RuizhiClient()
    return _client


def _response_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:500]

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return str(message)
        if error:
            return str(error)
        message = payload.get("message")
        if message:
            return str(message)
    return str(payload)[:500]


def chat(
    messages: list[dict[str, Any]],
    model: str | None = None,
    stream: bool = False,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
) -> dict[str, Any] | Generator[dict[str, Any], None, None]:
    payload: dict[str, Any] = {
        "model": model or RUIZHI_TEXT_MODEL,
        "messages": messages,
        "stream": stream,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if tools is not None:
        payload["tools"] = tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice

    client = _get_client()
    if stream:
        return client.stream("/chat/completions", payload)
    return client.request("POST", "/chat/completions", json=payload)


def chat_with_kb(
    messages: list[dict[str, Any]],
    kb_names: list[str],
    model: str | None = None,
    stream: bool = False,
    max_tokens: int = 2000,
) -> dict[str, Any] | Generator[dict[str, Any], None, None]:
    kb_content = " ".join(f"@{name}" for name in kb_names)
    rag_messages = [*messages, {"role": "run", "content": kb_content}]
    return chat(rag_messages, model=model, stream=stream, max_tokens=max_tokens)


def embedding(
    texts: str | list[str],
    model: str | None = None,
    dimensions: int = 1024,
) -> list[list[float]]:
    payload = {
        "model": model or RUIZHI_EMBEDDING_MODEL,
        "input": texts,
        "dimensions": dimensions,
    }
    response = _get_client().request("POST", "/embeddings", json=payload)
    data = response.get("data", []) if isinstance(response, dict) else []
    if not isinstance(data, list):
        raise RuizhiApiError("Ruizhi embeddings response missing data list")

    ordered = sorted(data, key=lambda item: item.get("index", 0) if isinstance(item, dict) else 0)
    vectors: list[list[float]] = []
    for item in ordered:
        if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
            raise RuizhiApiError("Ruizhi embeddings response contains an invalid item")
        vectors.append(item["embedding"])
    return vectors


def rerank(
    query: str,
    documents: list[str],
    model: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    payload = {
        "model": model or RUIZHI_RERANK_MODEL,
        "query": query,
        "documents": documents,
        "top_k": top_k,
    }
    response = _get_client().request("POST", "/rerank", json=payload)
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        results = response.get("results", response.get("data", []))
        if isinstance(results, list):
            return [item for item in results if isinstance(item, dict)]
    raise RuizhiApiError("Ruizhi rerank response missing results list")


def list_models() -> list[dict[str, Any]]:
    response = _get_client().request("GET", "/models")
    if isinstance(response, dict):
        data = response.get("data", [])
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    raise RuizhiApiError("Ruizhi models response missing data list")
