"""Integration tests for the Advertiser endpoint using a mock HTTP transport."""

import json

import httpx
import pytest

from ttd_data import errors
from ttd_data.models import AdvertiserData, AdvertiserDataItem

from .conftest import SAMPLE_TOKEN, json_response

ADVERTISER_ID = "test_advertiser_123"


class TestIngestAdvertiserData:
    def test_200_success_returns_response(self, make_client):
        client = make_client(
            lambda _: json_response(200, {"FailedLines": []})
        )
        response = client.advertiser.ingest_advertiser_data(
            ttd_auth=SAMPLE_TOKEN,
            advertiser_id=ADVERTISER_ID,
            items=[AdvertiserDataItem(tdid="abc-123", data=[AdvertiserData(name="seg")])],
        )
        assert response.advertiser_data_server_response is not None

    def test_posts_to_correct_path(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            return json_response(200, {"FailedLines": []})

        client = make_client(handler)
        client.advertiser.ingest_advertiser_data(
            ttd_auth=SAMPLE_TOKEN, advertiser_id=ADVERTISER_ID
        )
        assert captured["path"] == "/data/advertiser"

    def test_sends_ttd_auth_header(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["ttd_auth"] = request.headers.get("ttd-auth")
            return json_response(200, {"FailedLines": []})

        client = make_client(handler)
        client.advertiser.ingest_advertiser_data(
            ttd_auth=SAMPLE_TOKEN, advertiser_id=ADVERTISER_ID
        )
        assert captured["ttd_auth"] == SAMPLE_TOKEN

    def test_request_body_contains_advertiser_id(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return json_response(200, {"FailedLines": []})

        client = make_client(handler)
        client.advertiser.ingest_advertiser_data(
            ttd_auth=SAMPLE_TOKEN, advertiser_id=ADVERTISER_ID
        )
        assert captured["body"]["AdvertiserId"] == ADVERTISER_ID

    def test_data_origins_hook_injects_sdk_origin(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return json_response(200, {"FailedLines": []})

        client = make_client(handler)
        client.advertiser.ingest_advertiser_data(
            ttd_auth=SAMPLE_TOKEN, advertiser_id=ADVERTISER_ID
        )
        origins = captured["body"].get("DataOrigins", [])
        assert any(o.get("Id") == "ttd_data_sdk" for o in origins)

    def test_400_raises_advertiser_data_server_response_error(self, make_client):
        client = make_client(
            lambda _: json_response(400, {"FailedLines": [{"LineNumber": 1}]})
        )
        with pytest.raises(errors.AdvertiserDataServerResponseError):
            client.advertiser.ingest_advertiser_data(
                ttd_auth=SAMPLE_TOKEN, advertiser_id=ADVERTISER_ID
            )

    def test_403_raises_api_error(self, make_client):
        client = make_client(
            lambda _: httpx.Response(403, content=b"Forbidden")
        )
        with pytest.raises(errors.APIError) as exc_info:
            client.advertiser.ingest_advertiser_data(
                ttd_auth="bad_token", advertiser_id=ADVERTISER_ID
            )
        assert exc_info.value.status_code == 403

    def test_500_raises_api_error(self, make_client):
        client = make_client(
            lambda _: httpx.Response(500, content=b"Internal Server Error")
        )
        with pytest.raises(errors.APIError) as exc_info:
            client.advertiser.ingest_advertiser_data(
                ttd_auth=SAMPLE_TOKEN, advertiser_id=ADVERTISER_ID
            )
        assert exc_info.value.status_code == 500

    def test_429_raises_advertiser_data_server_response_error(self, make_client):
        client = make_client(
            lambda _: json_response(429, {"FailedLines": []})
        )
        with pytest.raises(errors.AdvertiserDataServerResponseError):
            client.advertiser.ingest_advertiser_data(
                ttd_auth=SAMPLE_TOKEN, advertiser_id=ADVERTISER_ID
            )

    def test_failed_lines_parsed_on_400(self, make_client):
        client = make_client(
            lambda _: json_response(
                400, {"FailedLines": [{"LineNumber": 2, "Error": "invalid id"}]}
            )
        )
        with pytest.raises(errors.AdvertiserDataServerResponseError) as exc_info:
            client.advertiser.ingest_advertiser_data(
                ttd_auth=SAMPLE_TOKEN, advertiser_id=ADVERTISER_ID
            )
        assert exc_info.value.data.failed_lines is not None
