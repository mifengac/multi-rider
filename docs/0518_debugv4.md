# 0518 Debug V4

## STEP A - Ruizhi API retest with SSL verification disabled

Command used:

```powershell
$env:RUIZHI_API_KEY='[REDACTED]'
$env:RUIZHI_BASE_URL='https://10.2.164.106/v2'
$env:RUIZHI_EMBEDDING_MODEL='Qwen3-Embedding-0.6B'
$env:RUIZHI_RERANK_MODEL='bge-reranker-base'
python test_ruizhi_api.py --no-verify-ssl --timeout 60
```

Full output, with only API key redacted:

```text
======================================================================
RUIZHI API DIAGNOSTICS
======================================================================

======================================================================
TEST: Environment Variables
======================================================================
  ✓ API_KEY: [REDACTED]
  ✓ BASE_URL: https://10.2.164.106/v2
  ✓ TEXT_MODEL: ayenaspring-pro-001
  ✓ EMBEDDING_MODEL: Qwen3-Embedding-0.6B
  ✓ RERANK_MODEL: bge-reranker-base
  ✓ KB_NAME: wcnr_test_0518_083959
✅ PASS: All required environment variables are set
  API_KEY: [REDACTED]
  BASE_URL: https://10.2.164.106/v2
  TEXT_MODEL: ayenaspring-pro-001
  EMBEDDING_MODEL: Qwen3-Embedding-0.6B
  RERANK_MODEL: bge-reranker-base
  KB_NAME: wcnr_test_0518_083959

======================================================================
TEST: URL Validity
======================================================================
✅ PASS: URL format is valid
  base_url: https://10.2.164.106/v2
  normalized_url: https://10.2.164.106/v2/
  issues: [
  "None"
]

======================================================================
TEST: Basic Connectivity (No Auth)
======================================================================
  Attempting GET https://10.2.164.106/v2/models
❌ FAIL: Connection error
  url: https://10.2.164.106/v2/models
  error: HTTPSConnectionPool(host='10.2.164.106', port=443): Max retries exceeded with url: /v2/models (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1006)')))
  suggestions: [
  "Check if BASE_URL is correct and accessible",
  "Check if server is running",
  "Check firewall settings",
  "Check network connectivity"
]

======================================================================
TEST: Authentication
======================================================================
  Attempting GET https://10.2.164.106/v2/models with Authorization header
❌ FAIL: Request failed: SSLError
  url: https://10.2.164.106/v2/models
  error: HTTPSConnectionPool(host='10.2.164.106', port=443): Max retries exceeded with url: /v2/models (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1006)')))

======================================================================
TEST: Models Listing Endpoint
======================================================================
  Attempting GET https://10.2.164.106/v2/models
❌ FAIL: Models endpoint: Request failed: SSLError
  url: https://10.2.164.106/v2/models
  error: HTTPSConnectionPool(host='10.2.164.106', port=443): Max retries exceeded with url: /v2/models (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1006)')))

======================================================================
TEST: Chat Completions Endpoint
======================================================================
  Attempting POST https://10.2.164.106/v2/chat/completions
  Model: ayenaspring-pro-001
❌ FAIL: Chat endpoint: Request failed: SSLError
  url: https://10.2.164.106/v2/chat/completions
  error: HTTPSConnectionPool(host='10.2.164.106', port=443): Max retries exceeded with url: /v2/chat/completions (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1006)')))

======================================================================
TEST: Embeddings Endpoint
======================================================================
  Attempting POST https://10.2.164.106/v2/embeddings
  Model: Qwen3-Embedding-0.6B
❌ FAIL: Embeddings endpoint: Request failed: SSLError
  url: https://10.2.164.106/v2/embeddings
  error: HTTPSConnectionPool(host='10.2.164.106', port=443): Max retries exceeded with url: /v2/embeddings (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1006)')))

======================================================================
TEST: Rerank Endpoint
======================================================================
  Attempting POST https://10.2.164.106/v2/rerank
  Model: bge-reranker-base
❌ FAIL: Rerank endpoint: Request failed: SSLError
  url: https://10.2.164.106/v2/rerank
  error: HTTPSConnectionPool(host='10.2.164.106', port=443): Max retries exceeded with url: /v2/rerank (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1006)')))

======================================================================
TEST SUMMARY
======================================================================

Total Tests: 8
Passed: 2 ✅
Failed: 6 ❌
Success Rate: 25.0%

❌ 6 test(s) failed. See details above for troubleshooting.

======================================================================
```

Supplemental timing probe:

```text
Base URL: https://10.2.164.106/v2
Output dir: ruizhi_api_test_out
Tests: embeddings, rerank

[FAIL] embeddings                       status=- elapsed=5025ms Network or local IO error
[FAIL] rerank                           status=- elapsed=5015ms Network or local IO error

Summary: passed=0, failed=2, report=ruizhi_api_test_out\report.json
Failed tests:
  - embeddings: status=-, detail=Network or local IO error, error=<urlopen error [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1006)>
  - rerank: status=-, detail=Network or local IO error, error=<urlopen error [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1006)>
```

Network evidence:

```text
Test-NetConnection 10.2.164.106:443 => TcpTestSucceeded=True
curl.exe -k https://10.2.164.106/v2/models => schannel: failed to receive handshake, SSL/TLS connection failed
requests with verify=False and trust_env=False => SSLError after 5032ms
```

Conclusion:

- Embeddings are not usable from this machine in the current retest. The endpoint did not return a vector, so the vector dimension cannot be determined from this run.
- Rerank is not usable from this machine in the current retest. The endpoint failed before any HTTP status or rerank result was returned.
- The failure moved past the previous certificate verification mismatch, but disabling certificate verification is not sufficient now: the TLS connection is closed during handshake with `UNEXPECTED_EOF_WHILE_READING`.
