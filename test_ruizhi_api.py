#!/usr/bin/env python3
"""
Ruizhi API Connection and Authentication Diagnostic Script

This script tests the Ruizhi API connection, verifies authentication,
and diagnoses common issues like 401/403 errors.

Usage:
    python test_ruizhi_api.py
    python test_ruizhi_api.py --api-key "your_key" --base-url "https://..."
    python test_ruizhi_api.py --help
"""

import os
import sys
import argparse
import logging
import json
from typing import Optional, Dict, Any
import traceback

# Handle encoding for Windows (GBK) terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() in ('gbk', 'gb2312', 'cp936'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import requests
    from requests.exceptions import RequestException, Timeout, ConnectionError
except ImportError:
    print("ERROR: 'requests' library is not installed.")
    print("Please install it with: pip install requests")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class RuizhiApiDiagnostics:
    """Diagnostic tool for Ruizhi API connections."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        text_model: Optional[str] = None,
        embedding_model: Optional[str] = None,
        rerank_model: Optional[str] = None,
        kb_name: Optional[str] = None,
        timeout: int = 10,
        verify_ssl: bool = True,
    ):
        """
        Initialize the diagnostics tool.

        Args:
            api_key: Ruizhi API key (loads from RUIZHI_API_KEY env var if not provided)
            base_url: Ruizhi base URL (loads from RUIZHI_BASE_URL env var if not provided)
            text_model: Text model name for chat completions
            embedding_model: Embedding model name
            rerank_model: Rerank model name
            kb_name: Knowledge base name
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.api_key = (api_key or "").strip() or os.getenv("RUIZHI_API_KEY", "")
        self.base_url = (base_url or "").strip() or os.getenv("RUIZHI_BASE_URL", "")
        self.text_model = (text_model or "").strip() or os.getenv("RUIZHI_TEXT_MODEL", "ayenaspring-pro-001")
        self.embedding_model = (embedding_model or "").strip() or os.getenv(
            "RUIZHI_EMBEDDING_MODEL", "Qwen3-Embedding-0.6B"
        )
        self.rerank_model = (rerank_model or "").strip() or os.getenv("RUIZHI_RERANK_MODEL", "bge-reranker-base")
        self.kb_name = (kb_name or "").strip() or os.getenv("RUIZHI_KB_NAME", "wcnr_test_0518_083959")
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # Results tracking
        self.results: Dict[str, Dict[str, Any]] = {}
        self.passed_tests = 0
        self.failed_tests = 0

    def _normalize_url(self, path: str) -> str:
        """Normalize and combine base URL with path."""
        base = self.base_url.rstrip("/")
        path = path.lstrip("/")
        return f"{base}/{path}"

    def _format_response(self, response_obj: requests.Response, max_length: int = 500) -> str:
        """Format response for display."""
        try:
            content = response_obj.text
            if len(content) > max_length:
                return content[:max_length] + f"\n... (truncated, total length: {len(content)})"
            return content
        except Exception:
            return "<unable to decode response>"

    def _print_test_header(self, test_name: str) -> None:
        """Print a test header."""
        print(f"\n{'=' * 70}")
        print(f"TEST: {test_name}")
        print("=" * 70)

    def _log_result(self, test_name: str, passed: bool, message: str, details: Dict[str, Any] = None) -> None:
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {message}")

        if details:
            for key, value in details.items():
                if isinstance(value, (dict, list)):
                    print(f"  {key}: {json.dumps(value, indent=2, ensure_ascii=False)}")
                else:
                    print(f"  {key}: {value}")

        if test_name not in self.results:
            self.results[test_name] = {}

        self.results[test_name]["passed"] = passed
        self.results[test_name]["message"] = message
        self.results[test_name]["details"] = details or {}

        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1

    def test_environment_variables(self) -> None:
        """Test 1: Check environment variables."""
        self._print_test_header("Environment Variables")

        checks = {
            "API_KEY": self.api_key,
            "BASE_URL": self.base_url,
            "TEXT_MODEL": self.text_model,
            "EMBEDDING_MODEL": self.embedding_model,
            "RERANK_MODEL": self.rerank_model,
            "KB_NAME": self.kb_name,
        }

        all_valid = True
        for name, value in checks.items():
            is_set = bool(value)
            status = "✓" if is_set else "✗"
            display = value[:50] + "..." if len(value) > 50 else value
            print(f"  {status} {name}: {display if is_set else '(not set)'}")
            if name in ["API_KEY", "BASE_URL"] and not is_set:
                all_valid = False

        if not self.api_key:
            self._log_result(
                "env_vars",
                False,
                "Missing RUIZHI_API_KEY environment variable",
                {"issue": "API_KEY is required but not set"},
            )
            return

        if not self.base_url:
            self._log_result(
                "env_vars",
                False,
                "Missing RUIZHI_BASE_URL environment variable",
                {"issue": "BASE_URL is required but not set"},
            )
            return

        self._log_result(
            "env_vars",
            True,
            "All required environment variables are set",
            checks,
        )

    def test_url_validity(self) -> None:
        """Test 2: Validate URL format."""
        self._print_test_header("URL Validity")

        if not self.base_url:
            print("  ⚠ Skipping: BASE_URL not set")
            return

        issues = []

        if not self.base_url.startswith(("http://", "https://")):
            issues.append("URL does not start with http:// or https://")

        if self.base_url.endswith("/"):
            issues.append("URL ends with '/' (will be stripped)")

        if " " in self.base_url:
            issues.append("URL contains spaces")

        passed = len(issues) == 0
        message = "URL format is valid" if passed else "URL format has issues"

        self._log_result(
            "url_validity",
            passed,
            message,
            {
                "base_url": self.base_url,
                "normalized_url": self._normalize_url(""),
                "issues": issues if issues else ["None"],
            },
        )

    def test_basic_connectivity(self) -> None:
        """Test 3: Test basic HTTP connectivity without authentication."""
        self._print_test_header("Basic Connectivity (No Auth)")

        if not self.base_url:
            print("  ⚠ Skipping: BASE_URL not set")
            return

        test_url = self._normalize_url("/models")

        try:
            print(f"  Attempting GET {test_url}")
            response = requests.get(
                test_url,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            print(f"  Status Code: {response.status_code}")

            passed = 200 <= response.status_code < 500  # Any response means connectivity works
            self._log_result(
                "basic_connectivity",
                passed,
                f"Basic connectivity test completed (status: {response.status_code})",
                {
                    "url": test_url,
                    "status_code": response.status_code,
                    "response_length": len(response.text),
                    "notes": "401/403 is expected without auth; 5xx means server issue",
                },
            )
        except Timeout:
            self._log_result(
                "basic_connectivity",
                False,
                "Request timeout",
                {
                    "url": test_url,
                    "timeout_seconds": self.timeout,
                    "suggestion": "Check network connectivity and server availability",
                },
            )
        except ConnectionError as e:
            self._log_result(
                "basic_connectivity",
                False,
                "Connection error",
                {
                    "url": test_url,
                    "error": str(e),
                    "suggestions": [
                        "Check if BASE_URL is correct and accessible",
                        "Check if server is running",
                        "Check firewall settings",
                        "Check network connectivity",
                    ],
                },
            )
        except RequestException as e:
            self._log_result(
                "basic_connectivity",
                False,
                f"Request failed: {type(e).__name__}",
                {
                    "url": test_url,
                    "error": str(e),
                },
            )

    def test_authentication(self) -> None:
        """Test 4: Test authentication with API key."""
        self._print_test_header("Authentication")

        if not self.base_url or not self.api_key:
            print("  ⚠ Skipping: BASE_URL or API_KEY not set")
            return

        test_url = self._normalize_url("/models")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            print(f"  Attempting GET {test_url} with Authorization header")
            response = requests.get(
                test_url,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            print(f"  Status Code: {response.status_code}")

            if response.status_code == 401:
                self._log_result(
                    "authentication",
                    False,
                    "Authentication failed (401 Unauthorized)",
                    {
                        "status_code": 401,
                        "url": test_url,
                        "possible_causes": [
                            "API key is invalid or expired",
                            "API key format is incorrect",
                            "API key lacks required permissions",
                            "API key has been revoked",
                        ],
                        "suggestions": [
                            "Verify the API key is correct",
                            "Check the API key has not expired",
                            "Contact API administrator to check permissions",
                            "Try regenerating the API key",
                        ],
                    },
                )
            elif response.status_code == 403:
                self._log_result(
                    "authentication",
                    False,
                    "Access forbidden (403 Forbidden)",
                    {
                        "status_code": 403,
                        "url": test_url,
                        "possible_causes": [
                            "Insufficient permissions for this endpoint",
                            "API key restricted to specific endpoints",
                            "Account has been disabled",
                        ],
                        "suggestions": [
                            "Check API key permissions",
                            "Request elevated privileges from administrator",
                        ],
                    },
                )
            elif 200 <= response.status_code < 300:
                self._log_result(
                    "authentication",
                    True,
                    "Authentication successful",
                    {
                        "status_code": response.status_code,
                        "response_length": len(response.text),
                    },
                )
            else:
                self._log_result(
                    "authentication",
                    False,
                    f"Unexpected status code: {response.status_code}",
                    {
                        "status_code": response.status_code,
                        "response_preview": self._format_response(response, 200),
                    },
                )
        except Timeout:
            self._log_result(
                "authentication",
                False,
                "Request timeout",
                {
                    "url": test_url,
                    "timeout_seconds": self.timeout,
                },
            )
        except RequestException as e:
            self._log_result(
                "authentication",
                False,
                f"Request failed: {type(e).__name__}",
                {
                    "url": test_url,
                    "error": str(e),
                },
            )

    def test_chat_endpoint(self) -> None:
        """Test 5: Test chat/completions endpoint."""
        self._print_test_header("Chat Completions Endpoint")

        if not self.base_url or not self.api_key:
            print("  ⚠ Skipping: BASE_URL or API_KEY not set")
            return

        test_url = self._normalize_url("/chat/completions")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.text_model,
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "max_tokens": 100,
        }

        try:
            print(f"  Attempting POST {test_url}")
            print(f"  Model: {self.text_model}")
            response = requests.post(
                test_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            print(f"  Status Code: {response.status_code}")

            if response.status_code == 401:
                self._log_result(
                    "chat_endpoint",
                    False,
                    "Chat endpoint: Authentication failed (401)",
                    {
                        "url": test_url,
                        "status_code": 401,
                    },
                )
            elif response.status_code == 404:
                self._log_result(
                    "chat_endpoint",
                    False,
                    "Chat endpoint: Not found (404)",
                    {
                        "url": test_url,
                        "status_code": 404,
                        "suggestion": "Check if the endpoint path is correct",
                    },
                )
            elif 200 <= response.status_code < 300:
                self._log_result(
                    "chat_endpoint",
                    True,
                    "Chat endpoint: Request successful",
                    {
                        "status_code": response.status_code,
                        "url": test_url,
                        "response_length": len(response.text),
                    },
                )
            else:
                self._log_result(
                    "chat_endpoint",
                    False,
                    f"Chat endpoint: Unexpected status {response.status_code}",
                    {
                        "status_code": response.status_code,
                        "url": test_url,
                        "response_preview": self._format_response(response, 200),
                    },
                )
        except Timeout:
            self._log_result(
                "chat_endpoint",
                False,
                "Chat endpoint: Request timeout",
                {
                    "url": test_url,
                    "timeout_seconds": self.timeout,
                },
            )
        except RequestException as e:
            self._log_result(
                "chat_endpoint",
                False,
                f"Chat endpoint: Request failed: {type(e).__name__}",
                {
                    "url": test_url,
                    "error": str(e),
                },
            )

    def test_embeddings_endpoint(self) -> None:
        """Test 6: Test embeddings endpoint."""
        self._print_test_header("Embeddings Endpoint")

        if not self.base_url or not self.api_key:
            print("  ⚠ Skipping: BASE_URL or API_KEY not set")
            return

        test_url = self._normalize_url("/embeddings")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.embedding_model,
            "input": "This is a test sentence for embeddings.",
        }

        try:
            print(f"  Attempting POST {test_url}")
            print(f"  Model: {self.embedding_model}")
            response = requests.post(
                test_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            print(f"  Status Code: {response.status_code}")

            if response.status_code == 401:
                self._log_result(
                    "embeddings_endpoint",
                    False,
                    "Embeddings endpoint: Authentication failed (401)",
                    {
                        "url": test_url,
                        "status_code": 401,
                    },
                )
            elif response.status_code == 404:
                self._log_result(
                    "embeddings_endpoint",
                    False,
                    "Embeddings endpoint: Not found (404)",
                    {
                        "url": test_url,
                        "status_code": 404,
                        "suggestion": "Endpoint may not be available or model name is incorrect",
                    },
                )
            elif 200 <= response.status_code < 300:
                self._log_result(
                    "embeddings_endpoint",
                    True,
                    "Embeddings endpoint: Request successful",
                    {
                        "status_code": response.status_code,
                        "url": test_url,
                        "response_length": len(response.text),
                    },
                )
            else:
                self._log_result(
                    "embeddings_endpoint",
                    False,
                    f"Embeddings endpoint: Unexpected status {response.status_code}",
                    {
                        "status_code": response.status_code,
                        "url": test_url,
                        "response_preview": self._format_response(response, 200),
                    },
                )
        except Timeout:
            self._log_result(
                "embeddings_endpoint",
                False,
                "Embeddings endpoint: Request timeout",
                {
                    "url": test_url,
                    "timeout_seconds": self.timeout,
                },
            )
        except RequestException as e:
            self._log_result(
                "embeddings_endpoint",
                False,
                f"Embeddings endpoint: Request failed: {type(e).__name__}",
                {
                    "url": test_url,
                    "error": str(e),
                },
            )

    def test_rerank_endpoint(self) -> None:
        """Test 7: Test rerank endpoint."""
        self._print_test_header("Rerank Endpoint")

        if not self.base_url or not self.api_key:
            print("  ⚠ Skipping: BASE_URL or API_KEY not set")
            return

        test_url = self._normalize_url("/rerank")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.rerank_model,
            "query": "What is the meaning of life?",
            "documents": [
                "The meaning of life is to be happy.",
                "Python is a programming language.",
            ],
        }

        try:
            print(f"  Attempting POST {test_url}")
            print(f"  Model: {self.rerank_model}")
            response = requests.post(
                test_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            print(f"  Status Code: {response.status_code}")

            if response.status_code == 401:
                self._log_result(
                    "rerank_endpoint",
                    False,
                    "Rerank endpoint: Authentication failed (401)",
                    {
                        "url": test_url,
                        "status_code": 401,
                    },
                )
            elif response.status_code == 404:
                self._log_result(
                    "rerank_endpoint",
                    False,
                    "Rerank endpoint: Not found (404)",
                    {
                        "url": test_url,
                        "status_code": 404,
                        "suggestion": "Endpoint may not be available or model name is incorrect",
                    },
                )
            elif 200 <= response.status_code < 300:
                self._log_result(
                    "rerank_endpoint",
                    True,
                    "Rerank endpoint: Request successful",
                    {
                        "status_code": response.status_code,
                        "url": test_url,
                        "response_length": len(response.text),
                    },
                )
            else:
                self._log_result(
                    "rerank_endpoint",
                    False,
                    f"Rerank endpoint: Unexpected status {response.status_code}",
                    {
                        "status_code": response.status_code,
                        "url": test_url,
                        "response_preview": self._format_response(response, 200),
                    },
                )
        except Timeout:
            self._log_result(
                "rerank_endpoint",
                False,
                "Rerank endpoint: Request timeout",
                {
                    "url": test_url,
                    "timeout_seconds": self.timeout,
                },
            )
        except RequestException as e:
            self._log_result(
                "rerank_endpoint",
                False,
                f"Rerank endpoint: Request failed: {type(e).__name__}",
                {
                    "url": test_url,
                    "error": str(e),
                },
            )

    def test_models_endpoint(self) -> None:
        """Test 8: Test /models endpoint to list available models."""
        self._print_test_header("Models Listing Endpoint")

        if not self.base_url or not self.api_key:
            print("  ⚠ Skipping: BASE_URL or API_KEY not set")
            return

        test_url = self._normalize_url("/models")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            print(f"  Attempting GET {test_url}")
            response = requests.get(
                test_url,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            print(f"  Status Code: {response.status_code}")

            if response.status_code == 401:
                self._log_result(
                    "models_endpoint",
                    False,
                    "Models endpoint: Authentication failed (401)",
                    {
                        "url": test_url,
                        "status_code": 401,
                    },
                )
            elif 200 <= response.status_code < 300:
                try:
                    models_data = response.json()
                    self._log_result(
                        "models_endpoint",
                        True,
                        "Models endpoint: Successfully retrieved available models",
                        {
                            "status_code": response.status_code,
                            "url": test_url,
                            "models_count": len(models_data.get("data", [])) if isinstance(models_data, dict) else 0,
                        },
                    )
                except json.JSONDecodeError:
                    self._log_result(
                        "models_endpoint",
                        False,
                        "Models endpoint: Response is not valid JSON",
                        {
                            "status_code": response.status_code,
                            "url": test_url,
                        },
                    )
            else:
                self._log_result(
                    "models_endpoint",
                    False,
                    f"Models endpoint: Unexpected status {response.status_code}",
                    {
                        "status_code": response.status_code,
                        "url": test_url,
                    },
                )
        except Timeout:
            self._log_result(
                "models_endpoint",
                False,
                "Models endpoint: Request timeout",
                {
                    "url": test_url,
                    "timeout_seconds": self.timeout,
                },
            )
        except RequestException as e:
            self._log_result(
                "models_endpoint",
                False,
                f"Models endpoint: Request failed: {type(e).__name__}",
                {
                    "url": test_url,
                    "error": str(e),
                },
            )

    def print_summary(self) -> None:
        """Print a summary of all tests."""
        print(f"\n{'=' * 70}")
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"\nTotal Tests: {self.passed_tests + self.failed_tests}")
        print(f"Passed: {self.passed_tests} ✅")
        print(f"Failed: {self.failed_tests} ❌")
        print(f"Success Rate: {(self.passed_tests / (self.passed_tests + self.failed_tests) * 100):.1f}%" if (self.passed_tests + self.failed_tests) > 0 else "N/A")

        if self.failed_tests == 0:
            print("\n✅ All tests passed! API connection and authentication are working correctly.")
        else:
            print(f"\n❌ {self.failed_tests} test(s) failed. See details above for troubleshooting.")

        print("\n" + "=" * 70)

    def run_all_tests(self) -> int:
        """Run all diagnostics tests."""
        print("\n" + "=" * 70)
        print("RUIZHI API DIAGNOSTICS")
        print("=" * 70)

        try:
            self.test_environment_variables()
            self.test_url_validity()
            self.test_basic_connectivity()
            self.test_authentication()
            self.test_models_endpoint()
            self.test_chat_endpoint()
            self.test_embeddings_endpoint()
            self.test_rerank_endpoint()

            self.print_summary()

            return 0 if self.failed_tests == 0 else 1
        except KeyboardInterrupt:
            print("\n\nDiagnostics interrupted by user.")
            return 1
        except Exception as e:
            print(f"\n\nUnexpected error during diagnostics: {e}")
            traceback.print_exc()
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Diagnose Ruizhi API connection and authentication issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_ruizhi_api.py
  python test_ruizhi_api.py --api-key "sk-xxx" --base-url "https://api.example.com/v2"
  python test_ruizhi_api.py --help
        """,
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Ruizhi API key (defaults to RUIZHI_API_KEY env var)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Ruizhi base URL (defaults to RUIZHI_BASE_URL env var)",
    )
    parser.add_argument(
        "--text-model",
        type=str,
        default=None,
        help="Text model name (defaults to RUIZHI_TEXT_MODEL env var)",
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default=None,
        help="Embedding model name (defaults to RUIZHI_EMBEDDING_MODEL env var)",
    )
    parser.add_argument(
        "--rerank-model",
        type=str,
        default=None,
        help="Rerank model name (defaults to RUIZHI_RERANK_MODEL env var)",
    )
    parser.add_argument(
        "--kb-name",
        type=str,
        default=None,
        help="Knowledge base name (defaults to RUIZHI_KB_NAME env var)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL certificate verification (useful for self-signed certs)",
    )

    args = parser.parse_args()

    diagnostics = RuizhiApiDiagnostics(
        api_key=args.api_key,
        base_url=args.base_url,
        text_model=args.text_model,
        embedding_model=args.embedding_model,
        rerank_model=args.rerank_model,
        kb_name=args.kb_name,
        timeout=args.timeout,
        verify_ssl=not args.no_verify_ssl,
    )

    exit_code = diagnostics.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
