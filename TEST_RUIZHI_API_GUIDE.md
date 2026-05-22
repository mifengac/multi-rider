# Ruizhi API Diagnostic Script Guide

## Overview

`test_ruizhi_api.py` is a standalone diagnostic script for testing Ruizhi API connections, validating authentication, and troubleshooting common issues like 401/403 errors.

## Installation

The script requires only the standard `requests` library:

```bash
pip install requests
```

Or if using `uv`:

```bash
uv pip install requests
```

## Quick Start

### Basic Usage (Uses Environment Variables)

```bash
python test_ruizhi_api.py
```

This will automatically load configuration from these environment variables:
- `RUIZHI_API_KEY` - Your API key
- `RUIZHI_BASE_URL` - API base URL (e.g., `https://10.2.164.106/v2`)
- `RUIZHI_TEXT_MODEL` - Text model name
- `RUIZHI_EMBEDDING_MODEL` - Embedding model name
- `RUIZHI_RERANK_MODEL` - Rerank model name
- `RUIZHI_KB_NAME` - Knowledge base name

### Override Configuration via Command Line

```bash
# Override API key and base URL
python test_ruizhi_api.py --api-key "your_api_key" --base-url "https://10.2.164.106/v2"

# Override multiple settings
python test_ruizhi_api.py \
    --api-key "your_api_key" \
    --base-url "https://10.2.164.106/v2" \
    --text-model "your-model-name" \
    --timeout 15

# Disable SSL verification (for self-signed certificates)
python test_ruizhi_api.py --no-verify-ssl
```

### View Help

```bash
python test_ruizhi_api.py --help
```

## Tests Performed

The script runs 8 comprehensive diagnostic tests:

### 1. **Environment Variables**
   - Checks if required env vars are set
   - Validates API key and base URL presence
   - Status: ✅ Pass / ❌ Fail

### 2. **URL Validity**
   - Validates base URL format
   - Checks for HTTP/HTTPS protocol
   - Detects URL formatting issues
   - Status: ✅ Pass / ❌ Fail

### 3. **Basic Connectivity (No Auth)**
   - Tests HTTP connectivity to the API server
   - Does not require authentication
   - Helps identify network/firewall issues
   - Status: ✅ Pass / ⚠️ Partial (401/403 is expected)

### 4. **Authentication**
   - Tests API key authentication with Bearer token
   - Detects 401 (Unauthorized) errors
   - Detects 403 (Forbidden) errors
   - Provides diagnostic suggestions for each error
   - Status: ✅ Pass / ❌ Fail

### 5. **Models Endpoint (/models)**
   - Tests listing available models
   - Requires valid authentication
   - Returns count of available models
   - Status: ✅ Pass / ❌ Fail

### 6. **Chat Completions (/chat/completions)**
   - Tests chat API endpoint
   - Sends simple test message
   - Verifies model availability and permissions
   - Status: ✅ Pass / ❌ Fail

### 7. **Embeddings (/embeddings)**
   - Tests embedding generation endpoint
   - Verifies embedding model configuration
   - Status: ✅ Pass / ❌ Fail

### 8. **Rerank (/rerank)**
   - Tests document reranking endpoint
   - Verifies rerank model configuration
   - Status: ✅ Pass / ❌ Fail

## Output Format

The script provides clear, step-by-step output:

```
======================================================================
TEST: Environment Variables
======================================================================
  ✓ API_KEY: sk-...
  ✓ BASE_URL: https://10.2.164.106/v2
  ✓ TEXT_MODEL: ayenaspring-pro-001
  ...
✅ PASS: All required environment variables are set

======================================================================
RUIZHI API DIAGNOSTICS
======================================================================
...
[Test details for each test]
...

======================================================================
TEST SUMMARY
======================================================================

Total Tests: 8
Passed: 7 ✅
Failed: 1 ❌
Success Rate: 87.5%

❌ 1 test(s) failed. See details above for troubleshooting.
```

## Troubleshooting Guide

### 401 Unauthorized Error

**Symptoms:**
- All or most tests fail with 401 status code
- "Authentication failed" message

**Possible Causes:**
1. API key is invalid or malformed
2. API key has expired
3. API key lacks required permissions
4. API key has been revoked

**Solutions:**
1. Verify the API key is correct: `echo $RUIZHI_API_KEY` (Linux/Mac) or `$env:RUIZHI_API_KEY` (PowerShell)
2. Check if API key has expired (check with API provider)
3. Regenerate or refresh the API key if necessary
4. Contact API administrator to verify permissions
5. Try with `--api-key "new_key"` to test a different key

### 403 Forbidden Error

**Symptoms:**
- Tests fail with 403 status code
- "Access forbidden" message

**Possible Causes:**
1. API key has insufficient permissions
2. API key is restricted to specific endpoints
3. Account has been disabled
4. IP address is blocked

**Solutions:**
1. Verify API key permissions with administrator
2. Check if your IP is whitelisted (if applicable)
3. Request elevated privileges if needed
4. Verify account is active

### Connection Timeout

**Symptoms:**
- "Request timeout" message
- Tests hang or take very long

**Possible Causes:**
1. Server is slow or offline
2. Network connectivity issues
3. Firewall blocking the connection
4. Very slow internet connection

**Solutions:**
1. Check if the API server is running: `ping 10.2.164.106` (if network allows)
2. Verify BASE_URL is correct
3. Increase timeout: `python test_ruizhi_api.py --timeout 30`
4. Check firewall/proxy settings
5. Test network connectivity with a simple ping or curl

### Connection Error

**Symptoms:**
- "Connection error" or "ConnectionRefused" message
- Cannot reach the server at all

**Possible Causes:**
1. Server is not running
2. BASE_URL is incorrect
3. Server port is wrong
4. Firewall is blocking the connection

**Solutions:**
1. Verify BASE_URL: `echo $RUIZHI_BASE_URL` (or PowerShell equivalent)
2. Check if the server is running on the specified address
3. Try accessing the URL directly in a browser (if accessible)
4. Check firewall/security group settings
5. Verify network connectivity to the server

### Invalid URL Format

**Symptoms:**
- "URL format has issues" message
- URL validation fails

**Possible Causes:**
1. URL missing http:// or https://
2. URL has typos
3. URL contains spaces or special characters

**Solutions:**
1. Ensure URL starts with `http://` or `https://`
2. Use correct format: `https://10.2.164.106/v2`
3. Remove trailing slashes: ✓ `https://10.2.164.106/v2` ✗ `https://10.2.164.106/v2/`

### SSL Certificate Issues

**Symptoms:**
- SSL error when connecting to HTTPS URLs
- "CERTIFICATE_VERIFY_FAILED" error

**Possible Causes:**
1. Self-signed certificate on server
2. Certificate chain issues
3. System trust store not updated

**Solutions:**
1. Use `--no-verify-ssl` flag (for testing only): `python test_ruizhi_api.py --no-verify-ssl`
2. Add server certificate to system trust store (production)
3. Contact server administrator about certificate issues

## Exit Codes

- `0` - All tests passed, API is working correctly
- `1` - One or more tests failed, see output for details

## Tips and Best Practices

1. **Start with basic tests first** - If basic connectivity fails, other tests will also fail
2. **Test with environment variables first** - Don't hardcode credentials in commands
3. **Use --timeout for slow networks** - Default is 10 seconds
4. **Check logs** - Enable verbose logging if needed
5. **Test from the server** - Run the script on the same machine as the Flask app to eliminate network variables
6. **Save output for debugging** - Redirect output to a file: `python test_ruizhi_api.py > diagnostic_output.txt 2>&1`

## Example Diagnostic Session

```bash
# 1. First, check if environment variables are loaded
python test_ruizhi_api.py

# If authentication fails, verify the key:
echo $RUIZHI_API_KEY

# Test with a known good key temporarily:
python test_ruizhi_api.py --api-key "test_key_value" --base-url "https://10.2.164.106/v2"

# If still failing, try with SSL disabled (self-signed cert):
python test_ruizhi_api.py --no-verify-ssl

# For slow networks, increase timeout:
python test_ruizhi_api.py --timeout 30
```

## Integration with Flask App

To automatically test the Ruizhi API when starting the Flask application:

1. Place `test_ruizhi_api.py` in the project root
2. Before starting `python app.py`, run:
   ```bash
   python test_ruizhi_api.py
   ```
3. Check the exit code to determine if API is available
4. If tests fail, review the output and troubleshoot before launching the app

## Support and Debugging

For detailed debugging:

1. Add environment variable to enable verbose output:
   ```bash
   DEBUG=1 python test_ruizhi_api.py
   ```

2. Capture full output to file:
   ```bash
   python test_ruizhi_api.py > diagnosis.log 2>&1
   ```

3. Include the output when reporting issues to support

## Related Configuration

See `shared/config/config.py` for the following Ruizhi-related configuration:

```python
RUIZHI_API_KEY = os.getenv("RUIZHI_API_KEY", "")
RUIZHI_BASE_URL = os.getenv("RUIZHI_BASE_URL", "https://10.2.164.106/v2")
RUIZHI_TEXT_MODEL = os.getenv("RUIZHI_TEXT_MODEL", "ayenaspring-pro-001")
RUIZHI_EMBEDDING_MODEL = os.getenv("RUIZHI_EMBEDDING_MODEL", "Qwen3-Embedding-0.6B")
RUIZHI_RERANK_MODEL = os.getenv("RUIZHI_RERANK_MODEL", "bge-reranker-base")
RUIZHI_KB_NAME = os.getenv("RUIZHI_KB_NAME", "wcnr_test_0518_083959")
```
