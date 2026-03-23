"""Tests for the PlainTextErrorNormalizer patch hook.

Unit tests verify the hook logic directly with no network calls.
The integration smoke test confirms the hook is registered and runs end-to-end tests.

Configure via environment variables:
  TTD_AUTH_TOKEN   - Valid API auth token (required for the integration smoke test)
  TEST_MERCHANT_ID - Valid merchant ID (default: 11449)
"""

import json
import os
import unittest

import httpx

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

TTD_AUTH_TOKEN = os.getenv("TTD_AUTH_TOKEN", "")
MERCHANT_ID = int(os.getenv("TEST_MERCHANT_ID", "11449"))

SAMPLE_TDID = "df2df528-e032-4851-b7c6-99287c7d6bce"


# ==============================================================================
# Unit Tests
# ==============================================================================


class TestPlainTextErrorNormalizerHook(unittest.TestCase):
    """Unit tests for PlainTextErrorNormalizer — no network calls."""

    def setUp(self):
        from ttd_data._hooks.plain_text_error_normalizer import PlainTextErrorNormalizer
        self.hook = PlainTextErrorNormalizer()

    def _make_response(self, status_code, body, content_type=None):
        headers = {"content-type": content_type} if content_type else {}
        content = body.encode("utf-8") if body else b""
        request = httpx.Request("POST", "https://example.com")
        return httpx.Response(status_code=status_code, headers=headers, content=content, request=request)

    def test_json_content_type_and_json_body_passthrough(self):
        """If content-type is already application/json, response is returned unchanged."""
        response = self._make_response(400, '{"error": "bad request"}', "application/json")
        result, _ = self.hook.after_error(hook_ctx=None, response=response, error=None)
        self.assertIs(result, response)

    def test_no_content_type_json_body(self):
        """If content-type is missing but body is valid JSON, set content-type and keep body as-is."""
        response = self._make_response(400, '{"error": "bad request"}')
        result, _ = self.hook.after_error(hook_ctx=None, response=response, error=None)
        self.assertIn("application/json", result.headers.get("content-type", ""))
        self.assertEqual(json.loads(result.text), {"error": "bad request"})

    def test_no_content_type_string_body(self):
        """If content-type is missing and body is plain text, wrap it as {message: ...}."""
        response = self._make_response(400, "Something went wrong")
        result, _ = self.hook.after_error(hook_ctx=None, response=response, error=None)
        self.assertIn("application/json", result.headers.get("content-type", ""))
        self.assertEqual(json.loads(result.text), {"message": "Something went wrong"})

    def test_no_content_type_no_body_passthrough(self):
        """If there is no body, response is returned unchanged."""
        response = self._make_response(400, "")
        result, _ = self.hook.after_error(hook_ctx=None, response=response, error=None)
        self.assertIs(result, response)

    def test_content_length_correct_after_plain_text_wrap(self):
        """content-length must reflect the wrapped JSON body size, not the original plain-text size."""
        plain_text = "Something went wrong"
        response = self._make_response(400, plain_text)
        result, _ = self.hook.after_error(hook_ctx=None, response=response, error=None)
        expected_body = json.dumps({"message": plain_text}).encode("utf-8")
        self.assertEqual(int(result.headers["content-length"]), len(expected_body))

    def test_content_length_correct_after_json_passthrough(self):
        """content-length must remain accurate when the body is already valid JSON."""
        json_body = '{"error": "bad request"}'
        response = self._make_response(400, json_body)
        result, _ = self.hook.after_error(hook_ctx=None, response=response, error=None)
        self.assertEqual(int(result.headers["content-length"]), len(json_body.encode("utf-8")))


# ==============================================================================
# Integration Smoke Test
# ==============================================================================


class TestPlainTextErrorNormalizerIntegration(unittest.TestCase):
    """Smoke tests — confirms the hook is registered, doesn't break success responses, and normalizes real plain-text errors."""

    @unittest.skipUnless(TTD_AUTH_TOKEN, "TTD_AUTH_TOKEN not set")
    def test_200_hook_does_not_affect_success_response(self):
        """A successful 200 response is returned unchanged by the hook."""
        from ttd_data import DataClient
        from ttd_data.models import PartnerDsrDataItem

        with DataClient() as client:
            response = client.deletion_opt_out.data_subject_request_merchant_data(
                merchant_id=MERCHANT_ID,
                ttd_auth=TTD_AUTH_TOKEN,
                items=[PartnerDsrDataItem(tdid=SAMPLE_TDID)],
            )

        ct = response.http_meta.response.headers.get("content-type", "")
        self.assertIn("application/json", ct, f"Expected application/json content-type, got: {ct!r}")

    @unittest.skipUnless(TTD_AUTH_TOKEN, "TTD_AUTH_TOKEN not set")
    def test_plain_text_400_is_normalized_to_json(self):
        """Merchant ID 0 returns a plain-text 400 with no content-type.
        The hook should wrap it into JSON and set content-type to application/json.
        """
        from ttd_data import DataClient
        from ttd_data.errors import MerchantDsrResponseError
        from ttd_data.models import PartnerDsrDataItem

        with DataClient() as client:
            with self.assertRaises(MerchantDsrResponseError) as ctx:
                client.deletion_opt_out.data_subject_request_merchant_data(
                    merchant_id=0,
                    ttd_auth=TTD_AUTH_TOKEN,
                    items=[PartnerDsrDataItem(tdid=SAMPLE_TDID)],
                )

        error = ctx.exception
        ct = error.raw_response.headers.get("content-type", "")
        self.assertIn("application/json", ct, f"Expected application/json content-type, got: {ct!r}")
        try:
            json.loads(error.body)
        except (json.JSONDecodeError, ValueError) as exc:
            self.fail(f"Response body is not valid JSON: {exc}\nBody: {error.body!r}")


if __name__ == "__main__":
    unittest.main()
