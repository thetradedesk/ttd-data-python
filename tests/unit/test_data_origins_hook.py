"""Unit tests for DataOriginsHook — no network calls."""

import json
from unittest.mock import MagicMock

import httpx
import pytest

from ttd_data._hooks.data_origins_hook import (
    DataOriginsHook,
    _OPERATIONS,
    _TTD_DATA_ORIGIN,
)
from ttd_data._hooks.types import BeforeRequestContext, HookContext


def make_context(operation_id: str) -> BeforeRequestContext:
    hook_ctx = HookContext(
        config=MagicMock(),
        base_url="https://example.com",
        operation_id=operation_id,
        oauth2_scopes=None,
        security_source=None,
    )
    return BeforeRequestContext(hook_ctx)


def make_request(body: dict) -> httpx.Request:
    content = json.dumps(body).encode()
    return httpx.Request(
        "POST",
        "https://example.com/data/advertiser",
        headers={
            "content-length": str(len(content)),
            "content-type": "application/json",
        },
        content=content,
    )


class TestDataOriginsHook:
    def setup_method(self):
        self.hook = DataOriginsHook()

    def test_injects_sdk_origin_when_none_provided(self):
        ctx = make_context("IngestAdvertiserData")
        request = make_request({"AdvertiserId": "abc123"})
        result = self.hook.before_request(ctx, request)
        body = json.loads(result.content)
        assert body["DataOrigins"] == [_TTD_DATA_ORIGIN]

    def test_appends_to_existing_origins(self):
        other_origin = {"Type": "Integration", "Id": "ttd_databricks_sdk"}
        ctx = make_context("IngestAdvertiserData")
        request = make_request(
            {"AdvertiserId": "abc123", "DataOrigins": [other_origin]}
        )
        result = self.hook.before_request(ctx, request)
        body = json.loads(result.content)
        assert len(body["DataOrigins"]) == 2
        assert other_origin in body["DataOrigins"]
        assert _TTD_DATA_ORIGIN in body["DataOrigins"]

    def test_does_not_duplicate_sdk_origin(self):
        ctx = make_context("IngestAdvertiserData")
        request = make_request(
            {"AdvertiserId": "abc123", "DataOrigins": [_TTD_DATA_ORIGIN]}
        )
        result = self.hook.before_request(ctx, request)
        body = json.loads(result.content)
        assert body["DataOrigins"].count(_TTD_DATA_ORIGIN) == 1

    def test_empty_data_origins_list_gets_sdk_origin(self):
        ctx = make_context("IngestAdvertiserData")
        request = make_request({"AdvertiserId": "abc123", "DataOrigins": []})
        result = self.hook.before_request(ctx, request)
        body = json.loads(result.content)
        assert body["DataOrigins"] == [_TTD_DATA_ORIGIN]

    def test_skips_non_ingestion_operations(self):
        ctx = make_context("DataSubjectRequestAdvertiserData")
        request = make_request({"AdvertiserId": "abc123"})
        result = self.hook.before_request(ctx, request)
        assert result is request

    def test_updates_content_length_after_injection(self):
        ctx = make_context("IngestThirdPartyData")
        request = make_request({"DataProviderId": "prov1"})
        result = self.hook.before_request(ctx, request)
        assert int(result.headers["content-length"]) == len(result.content)

    @pytest.mark.parametrize("operation_id", sorted(_OPERATIONS))
    def test_applies_to_all_ingestion_operations(self, operation_id):
        ctx = make_context(operation_id)
        request = make_request({"DataProviderId": "prov1"})
        result = self.hook.before_request(ctx, request)
        body = json.loads(result.content)
        assert any(o.get("Id") == "ttd_data_sdk" for o in body["DataOrigins"])

    def test_preserves_other_body_fields(self):
        ctx = make_context("IngestAdvertiserData")
        request = make_request({"AdvertiserId": "abc123", "Items": [{"Tdid": "xyz"}]})
        result = self.hook.before_request(ctx, request)
        body = json.loads(result.content)
        assert body["AdvertiserId"] == "abc123"
        assert body["Items"] == [{"Tdid": "xyz"}]
