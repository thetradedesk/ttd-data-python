"""Integration tests for the DeletionOptOut endpoint using a mock HTTP transport."""

import json

import httpx
import pytest

from ttd_data import errors
from ttd_data.models import PartnerDsrDataItem, PartnerDsrRequestType

from .conftest import SAMPLE_TOKEN, json_response

ADVERTISER_ID = "test_advertiser_123"
DATA_PROVIDER_ID = "test_provider_456"
MERCHANT_ID = 11449
SAMPLE_TDID = "df2df528-e032-4851-b7c6-99287c7d6bce"


class TestDataSubjectRequestAdvertiserData:
    def test_200_success_returns_response(self, make_client):
        client = make_client(lambda _: json_response(200, {}))
        response = client.deletion_opt_out.data_subject_request_advertiser_data(
            ttd_auth=SAMPLE_TOKEN,
            advertiser_id=ADVERTISER_ID,
            items=[PartnerDsrDataItem(tdid=SAMPLE_TDID)],
            request_type=PartnerDsrRequestType.DELETION,
        )
        assert response.advertiser_dsr_response is not None or response.http_meta is not None

    def test_posts_to_correct_path(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            return json_response(200, {})

        client = make_client(handler)
        client.deletion_opt_out.data_subject_request_advertiser_data(
            ttd_auth=SAMPLE_TOKEN, advertiser_id=ADVERTISER_ID
        )
        assert captured["path"] == "/data/deletion-optout/advertiser"

    def test_request_type_sent_in_body(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return json_response(200, {})

        client = make_client(handler)
        client.deletion_opt_out.data_subject_request_advertiser_data(
            ttd_auth=SAMPLE_TOKEN,
            advertiser_id=ADVERTISER_ID,
            request_type=PartnerDsrRequestType.OPT_OUT,
        )
        assert captured["body"].get("RequestType") is not None

    def test_403_raises_api_error(self, make_client):
        client = make_client(lambda _: httpx.Response(403, content=b"Forbidden"))
        with pytest.raises(errors.APIError) as exc_info:
            client.deletion_opt_out.data_subject_request_advertiser_data(
                ttd_auth="bad_token", advertiser_id=ADVERTISER_ID
            )
        assert exc_info.value.status_code == 403

    def test_400_raises_advertiser_dsr_response_error(self, make_client):
        client = make_client(
            lambda _: json_response(400, {"FailedLines": [{"LineNumber": 1}]})
        )
        with pytest.raises(errors.AdvertiserDsrResponseError):
            client.deletion_opt_out.data_subject_request_advertiser_data(
                ttd_auth=SAMPLE_TOKEN, advertiser_id=ADVERTISER_ID
            )


class TestDataSubjectRequestMerchantData:
    def test_200_success_returns_response(self, make_client):
        client = make_client(lambda _: json_response(200, {}))
        response = client.deletion_opt_out.data_subject_request_merchant_data(
            ttd_auth=SAMPLE_TOKEN,
            merchant_id=MERCHANT_ID,
            items=[PartnerDsrDataItem(tdid=SAMPLE_TDID)],
        )
        assert response.http_meta is not None

    def test_posts_to_correct_path(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            return json_response(200, {})

        client = make_client(handler)
        client.deletion_opt_out.data_subject_request_merchant_data(
            ttd_auth=SAMPLE_TOKEN, merchant_id=MERCHANT_ID
        )
        assert captured["path"] == "/data/deletion-optout/merchant"

    def test_merchant_id_sent_in_body(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return json_response(200, {})

        client = make_client(handler)
        client.deletion_opt_out.data_subject_request_merchant_data(
            ttd_auth=SAMPLE_TOKEN, merchant_id=MERCHANT_ID
        )
        assert captured["body"]["MerchantId"] == MERCHANT_ID

    def test_400_raises_merchant_dsr_response_error(self, make_client):
        client = make_client(
            lambda _: json_response(400, {"FailedLines": [{"LineNumber": 1}]})
        )
        with pytest.raises(errors.MerchantDsrResponseError):
            client.deletion_opt_out.data_subject_request_merchant_data(
                ttd_auth=SAMPLE_TOKEN, merchant_id=MERCHANT_ID
            )

    def test_403_raises_api_error(self, make_client):
        client = make_client(lambda _: httpx.Response(403, content=b"Forbidden"))
        with pytest.raises(errors.APIError) as exc_info:
            client.deletion_opt_out.data_subject_request_merchant_data(
                ttd_auth="bad_token", merchant_id=MERCHANT_ID
            )
        assert exc_info.value.status_code == 403


class TestDataSubjectRequestThirdPartyData:
    def test_200_success_returns_response(self, make_client):
        client = make_client(lambda _: json_response(200, {}))
        response = client.deletion_opt_out.data_subject_request_third_party_data(
            ttd_auth=SAMPLE_TOKEN,
            data_provider_id=DATA_PROVIDER_ID,
            items=[PartnerDsrDataItem(tdid=SAMPLE_TDID)],
        )
        assert response.http_meta is not None

    def test_posts_to_correct_path(self, make_client):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            return json_response(200, {})

        client = make_client(handler)
        client.deletion_opt_out.data_subject_request_third_party_data(
            ttd_auth=SAMPLE_TOKEN, data_provider_id=DATA_PROVIDER_ID
        )
        assert captured["path"] == "/data/deletion-optout/thirdparty"

    def test_400_raises_third_party_dsr_response_error(self, make_client):
        client = make_client(
            lambda _: json_response(400, {"FailedLines": [{"LineNumber": 1}]})
        )
        with pytest.raises(errors.ThirdPartyDsrResponseError):
            client.deletion_opt_out.data_subject_request_third_party_data(
                ttd_auth=SAMPLE_TOKEN, data_provider_id=DATA_PROVIDER_ID
            )
