"""Integration tests for the OfflineConversion endpoint using a mock HTTP transport."""

import json
from datetime import datetime, timezone

import httpx
import pytest

from ttd_data import errors
from ttd_data.models import OfflineConversionDataItem

from .conftest import SAMPLE_TOKEN, json_response

DATA_PROVIDER_ID = "test_provider_456"
TRACKING_TAG_ID = "tag_abc"
TIMESTAMP = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


class TestIngestOfflineConversionData:
    def test_200_success_returns_response(self, make_client):
        client = make_client(
            lambda _: json_response(200, {"FailedLines": []})
        )
        response = client.offline_conversion.ingest_offline_conversion_data(
            ttd_auth=SAMPLE_TOKEN,
            data_provider_id=DATA_PROVIDER_ID,
            items=[
                OfflineConversionDataItem(
                    tracking_tag_id=TRACKING_TAG_ID,
                    timestamp_utc=TIMESTAMP,
                )
            ],
        )
        assert response.offline_conversion_data_server_response is not None

    def test_posts_to_correct_path(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            return json_response(200, {"FailedLines": []})

        client = make_client(handler)
        client.offline_conversion.ingest_offline_conversion_data(
            ttd_auth=SAMPLE_TOKEN, data_provider_id=DATA_PROVIDER_ID
        )
        assert captured["path"] == "/providerapi/offlineconversion"

    def test_sends_ttd_auth_header(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["ttd_auth"] = request.headers.get("ttd-auth")
            return json_response(200, {"FailedLines": []})

        client = make_client(handler)
        client.offline_conversion.ingest_offline_conversion_data(
            ttd_auth=SAMPLE_TOKEN, data_provider_id=DATA_PROVIDER_ID
        )
        assert captured["ttd_auth"] == SAMPLE_TOKEN

    def test_request_body_contains_data_provider_id(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return json_response(200, {"FailedLines": []})

        client = make_client(handler)
        client.offline_conversion.ingest_offline_conversion_data(
            ttd_auth=SAMPLE_TOKEN, data_provider_id=DATA_PROVIDER_ID
        )
        assert captured["body"]["DataProviderId"] == DATA_PROVIDER_ID

    def test_data_origins_hook_injects_sdk_origin(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return json_response(200, {"FailedLines": []})

        client = make_client(handler)
        client.offline_conversion.ingest_offline_conversion_data(
            ttd_auth=SAMPLE_TOKEN, data_provider_id=DATA_PROVIDER_ID
        )
        origins = captured["body"].get("DataOrigins", [])
        assert any(o.get("Id") == "ttd_data_sdk" for o in origins)

    def test_user_id_array_metadata_format_sent_in_body(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return json_response(200, {"FailedLines": []})

        client = make_client(handler)
        client.offline_conversion.ingest_offline_conversion_data(
            ttd_auth=SAMPLE_TOKEN,
            data_provider_id=DATA_PROVIDER_ID,
            user_id_array_metadata_format=["TDID", "UID2"],
        )
        assert captured["body"]["UserIdArrayMetadataFormat"] == ["TDID", "UID2"]

    def test_400_raises_offline_conversion_error(self, make_client):
        client = make_client(
            lambda _: json_response(400, {"FailedLines": [{"LineNumber": 1}]})
        )
        with pytest.raises(errors.OfflineConversionDataServerResponseError):
            client.offline_conversion.ingest_offline_conversion_data(
                ttd_auth=SAMPLE_TOKEN, data_provider_id=DATA_PROVIDER_ID
            )

    def test_403_raises_api_error(self, make_client):
        client = make_client(
            lambda _: httpx.Response(403, content=b"Forbidden")
        )
        with pytest.raises(errors.APIError) as exc_info:
            client.offline_conversion.ingest_offline_conversion_data(
                ttd_auth="bad_token", data_provider_id=DATA_PROVIDER_ID
            )
        assert exc_info.value.status_code == 403

    def test_500_raises_api_error(self, make_client):
        client = make_client(
            lambda _: httpx.Response(500, content=b"Internal Server Error")
        )
        with pytest.raises(errors.APIError) as exc_info:
            client.offline_conversion.ingest_offline_conversion_data(
                ttd_auth=SAMPLE_TOKEN, data_provider_id=DATA_PROVIDER_ID
            )
        assert exc_info.value.status_code == 500
