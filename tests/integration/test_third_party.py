"""Integration tests for the ThirdParty endpoint using a mock HTTP transport."""

import json

import httpx
import pytest

from ttd_data import errors
from ttd_data.models import ThirdPartyData, ThirdPartyDataItem

from .conftest import SAMPLE_TOKEN, json_response

DATA_PROVIDER_ID = "test_provider_456"


class TestIngestThirdPartyData:
    def test_200_success_returns_response(self, make_client):
        client = make_client(
            lambda _: json_response(200, {"FailedLines": []})
        )
        response = client.third_party.ingest_third_party_data(
            ttd_auth=SAMPLE_TOKEN,
            data_provider_id=DATA_PROVIDER_ID,
            items=[ThirdPartyDataItem(tdid="abc-123", data=[ThirdPartyData(name="seg")])],
        )
        assert response.third_party_data_server_response is not None

    def test_posts_to_correct_path(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            return json_response(200, {"FailedLines": []})

        client = make_client(handler)
        client.third_party.ingest_third_party_data(
            ttd_auth=SAMPLE_TOKEN, data_provider_id=DATA_PROVIDER_ID
        )
        assert captured["path"] == "/data/thirdparty"

    def test_sends_ttd_auth_header(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["ttd_auth"] = request.headers.get("ttd-auth")
            return json_response(200, {"FailedLines": []})

        client = make_client(handler)
        client.third_party.ingest_third_party_data(
            ttd_auth=SAMPLE_TOKEN, data_provider_id=DATA_PROVIDER_ID
        )
        assert captured["ttd_auth"] == SAMPLE_TOKEN

    def test_request_body_contains_data_provider_id(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return json_response(200, {"FailedLines": []})

        client = make_client(handler)
        client.third_party.ingest_third_party_data(
            ttd_auth=SAMPLE_TOKEN, data_provider_id=DATA_PROVIDER_ID
        )
        assert captured["body"]["DataProviderId"] == DATA_PROVIDER_ID

    def test_is_user_id_already_hashed_sent_in_body(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return json_response(200, {"FailedLines": []})

        client = make_client(handler)
        client.third_party.ingest_third_party_data(
            ttd_auth=SAMPLE_TOKEN,
            data_provider_id=DATA_PROVIDER_ID,
            is_user_id_already_hashed=True,
        )
        assert captured["body"]["IsUserIdAlreadyHashed"] is True

    def test_data_origins_hook_injects_sdk_origin(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return json_response(200, {"FailedLines": []})

        client = make_client(handler)
        client.third_party.ingest_third_party_data(
            ttd_auth=SAMPLE_TOKEN, data_provider_id=DATA_PROVIDER_ID
        )
        origins = captured["body"].get("DataOrigins", [])
        assert any(o.get("Id") == "ttd_data_sdk" for o in origins)

    def test_400_raises_third_party_data_server_response_error(self, make_client):
        client = make_client(
            lambda _: json_response(400, {"FailedLines": [{"LineNumber": 1}]})
        )
        with pytest.raises(errors.ThirdPartyDataServerResponseError):
            client.third_party.ingest_third_party_data(
                ttd_auth=SAMPLE_TOKEN, data_provider_id=DATA_PROVIDER_ID
            )

    def test_403_raises_api_error(self, make_client):
        client = make_client(
            lambda _: httpx.Response(403, content=b"Forbidden")
        )
        with pytest.raises(errors.APIError) as exc_info:
            client.third_party.ingest_third_party_data(
                ttd_auth="bad_token", data_provider_id=DATA_PROVIDER_ID
            )
        assert exc_info.value.status_code == 403

    def test_500_raises_api_error(self, make_client):
        client = make_client(
            lambda _: httpx.Response(500, content=b"Internal Server Error")
        )
        with pytest.raises(errors.APIError) as exc_info:
            client.third_party.ingest_third_party_data(
                ttd_auth=SAMPLE_TOKEN, data_provider_id=DATA_PROVIDER_ID
            )
        assert exc_info.value.status_code == 500
