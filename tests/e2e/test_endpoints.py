"""End-to-end tests that make real HTTP calls to the TTD Data API.

All tests are skipped automatically when TTD_AUTH_TOKEN is not set.

Configure via environment variables:
  TTD_AUTH_TOKEN        - Valid API auth token (required)
  TTD_DATA_SERVER_URL   - API base URL (default: https://usw-data.adsrvr.org)
  TEST_ADVERTISER_ID    - Valid advertiser ID (default: xjagv7s)
  TEST_DATA_PROVIDER_ID - Valid data provider ID (default: eltoro)
  TEST_TRACKING_TAG_ID  - Valid tracking tag ID (default: l1ustb2)
  TEST_MERCHANT_ID      - Valid merchant ID (default: 11449)

How 400s are triggered per endpoint:
  Advertiser          - invalid advertiser ID with valid token    → AdvertiserDataServerResponseError
  ThirdParty          - invalid auth token                       → ThirdPartyDataServerResponseError
  OfflineConversion   - invalid auth token                       → OfflineConversionDataServerResponseError
  DeletionOptOut/Adv  - invalid auth token                       → AdvertiserDsrResponseError
  DeletionOptOut/Merch- merchant_id=0 (not configured)          → MerchantDsrResponseError
  DeletionOptOut/3P   - invalid auth token                       → ThirdPartyDsrResponseError
"""

import os
from datetime import datetime, timezone

import pytest

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

TTD_AUTH_TOKEN = os.getenv("TTD_AUTH_TOKEN", "")
SERVER_URL = os.getenv("TTD_DATA_SERVER_URL", "https://usw-data.adsrvr.org")
ADVERTISER_ID = os.getenv("TEST_ADVERTISER_ID", "xjagv7s")
DATA_PROVIDER_ID = os.getenv("TEST_DATA_PROVIDER_ID", "eltoro")
TRACKING_TAG_ID = os.getenv("TEST_TRACKING_TAG_ID", "l1ustb2")
MERCHANT_ID = int(os.getenv("TEST_MERCHANT_ID", "11449"))

SAMPLE_TDID = "df2df528-e032-4851-b7c6-99287c7d6bce"
INVALID_ADVERTISER_ID = "invalid-advertiser-id-00000"
INVALID_AUTH_TOKEN = "invalid-auth-token-00000"

requires_token = pytest.mark.skipif(
    not TTD_AUTH_TOKEN, reason="TTD_AUTH_TOKEN not set"
)


# ---------------------------------------------------------------------------
# Advertiser  /data/advertiser
# ---------------------------------------------------------------------------


@requires_token
def test_advertiser_200():
    from ttd_data import DataClient
    from ttd_data.models import AdvertiserData, AdvertiserDataItem

    with DataClient(server_url=SERVER_URL) as client:
        response = client.advertiser.ingest_advertiser_data(
            ttd_auth=TTD_AUTH_TOKEN,
            advertiser_id=ADVERTISER_ID,
            items=[AdvertiserDataItem(tdid=SAMPLE_TDID, data=[AdvertiserData(name="test_segment")])],
        )

    assert response.http_meta.response.status_code == 200
    assert response.advertiser_data_server_response is not None


@requires_token
def test_advertiser_400_invalid_advertiser_id():
    from ttd_data import DataClient, errors
    from ttd_data.models import AdvertiserData, AdvertiserDataItem

    with DataClient(server_url=SERVER_URL) as client:
        with pytest.raises(errors.AdvertiserDataServerResponseError) as exc_info:
            client.advertiser.ingest_advertiser_data(
                ttd_auth=TTD_AUTH_TOKEN,
                advertiser_id=INVALID_ADVERTISER_ID,
                items=[AdvertiserDataItem(tdid=SAMPLE_TDID, data=[AdvertiserData(name="test_segment")])],
            )

    assert exc_info.value.raw_response.status_code == 400


# ---------------------------------------------------------------------------
# ThirdParty  /data/thirdparty
# ---------------------------------------------------------------------------


@requires_token
def test_third_party_200():
    from ttd_data import DataClient
    from ttd_data.models import ThirdPartyData, ThirdPartyDataItem

    with DataClient(server_url=SERVER_URL) as client:
        response = client.third_party.ingest_third_party_data(
            ttd_auth=TTD_AUTH_TOKEN,
            data_provider_id=DATA_PROVIDER_ID,
            items=[ThirdPartyDataItem(tdid=SAMPLE_TDID, data=[ThirdPartyData(name="test_segment")])],
        )

    assert response.http_meta.response.status_code == 200
    assert response.third_party_data_server_response is not None


@requires_token
def test_third_party_400_invalid_auth():
    from ttd_data import DataClient, errors
    from ttd_data.models import ThirdPartyData, ThirdPartyDataItem

    with DataClient(server_url=SERVER_URL) as client:
        with pytest.raises(errors.ThirdPartyDataServerResponseError) as exc_info:
            client.third_party.ingest_third_party_data(
                ttd_auth=INVALID_AUTH_TOKEN,
                data_provider_id=DATA_PROVIDER_ID,
                items=[ThirdPartyDataItem(tdid=SAMPLE_TDID, data=[ThirdPartyData(name="test_segment")])],
            )

    assert exc_info.value.raw_response.status_code == 400


# ---------------------------------------------------------------------------
# OfflineConversion  /providerapi/offlineconversion
# ---------------------------------------------------------------------------


@requires_token
def test_offline_conversion_200():
    from ttd_data import DataClient
    from ttd_data.models import OfflineConversionDataItem

    with DataClient(server_url=SERVER_URL) as client:
        response = client.offline_conversion.ingest_offline_conversion_data(
            ttd_auth=TTD_AUTH_TOKEN,
            data_provider_id=DATA_PROVIDER_ID,
            items=[
                OfflineConversionDataItem(
                    tracking_tag_id=TRACKING_TAG_ID,
                    timestamp_utc=datetime.now(timezone.utc),
                )
            ],
        )

    assert response.http_meta.response.status_code == 200
    assert response.offline_conversion_data_server_response is not None


@requires_token
def test_offline_conversion_400_invalid_auth():
    from ttd_data import DataClient, errors
    from ttd_data.models import OfflineConversionDataItem

    with DataClient(server_url=SERVER_URL) as client:
        with pytest.raises(errors.OfflineConversionDataServerResponseError) as exc_info:
            client.offline_conversion.ingest_offline_conversion_data(
                ttd_auth=INVALID_AUTH_TOKEN,
                data_provider_id=DATA_PROVIDER_ID,
                items=[
                    OfflineConversionDataItem(
                        tracking_tag_id=TRACKING_TAG_ID,
                        timestamp_utc=datetime.now(timezone.utc),
                    )
                ],
            )

    assert exc_info.value.raw_response.status_code == 400


# ---------------------------------------------------------------------------
# DeletionOptOut / Advertiser  /data/deletion-optout/advertiser
# ---------------------------------------------------------------------------


@requires_token
def test_deletion_optout_advertiser_200():
    from ttd_data import DataClient
    from ttd_data.models import PartnerDsrDataItem

    with DataClient(server_url=SERVER_URL) as client:
        response = client.deletion_opt_out.data_subject_request_advertiser_data(
            ttd_auth=TTD_AUTH_TOKEN,
            advertiser_id=ADVERTISER_ID,
            items=[PartnerDsrDataItem(tdid=SAMPLE_TDID)],
        )

    assert response.http_meta.response.status_code == 200


@requires_token
def test_deletion_optout_advertiser_400_invalid_auth():
    from ttd_data import DataClient, errors
    from ttd_data.models import PartnerDsrDataItem

    with DataClient(server_url=SERVER_URL) as client:
        with pytest.raises(errors.AdvertiserDsrResponseError) as exc_info:
            client.deletion_opt_out.data_subject_request_advertiser_data(
                ttd_auth=INVALID_AUTH_TOKEN,
                advertiser_id=ADVERTISER_ID,
                items=[PartnerDsrDataItem(tdid=SAMPLE_TDID)],
            )

    assert exc_info.value.raw_response.status_code == 400


# ---------------------------------------------------------------------------
# DeletionOptOut / Merchant  /data/deletion-optout/merchant
# ---------------------------------------------------------------------------


@requires_token
def test_deletion_optout_merchant_200():
    from ttd_data import DataClient
    from ttd_data.models import PartnerDsrDataItem

    with DataClient(server_url=SERVER_URL) as client:
        response = client.deletion_opt_out.data_subject_request_merchant_data(
            ttd_auth=TTD_AUTH_TOKEN,
            merchant_id=MERCHANT_ID,
            items=[PartnerDsrDataItem(tdid=SAMPLE_TDID)],
        )

    assert response.http_meta.response.status_code == 200


@requires_token
def test_deletion_optout_merchant_400_invalid_merchant_id():
    """merchant_id=0 is not configured and reliably returns 400."""
    from ttd_data import DataClient, errors
    from ttd_data.models import PartnerDsrDataItem

    with DataClient(server_url=SERVER_URL) as client:
        with pytest.raises(errors.MerchantDsrResponseError) as exc_info:
            client.deletion_opt_out.data_subject_request_merchant_data(
                ttd_auth=TTD_AUTH_TOKEN,
                merchant_id=0,
                items=[PartnerDsrDataItem(tdid=SAMPLE_TDID)],
            )

    assert exc_info.value.raw_response.status_code == 400


# ---------------------------------------------------------------------------
# DeletionOptOut / ThirdParty  /data/deletion-optout/thirdparty
# ---------------------------------------------------------------------------


@requires_token
def test_deletion_optout_third_party_200():
    from ttd_data import DataClient
    from ttd_data.models import PartnerDsrDataItem

    with DataClient(server_url=SERVER_URL) as client:
        response = client.deletion_opt_out.data_subject_request_third_party_data(
            ttd_auth=TTD_AUTH_TOKEN,
            data_provider_id=DATA_PROVIDER_ID,
            items=[PartnerDsrDataItem(tdid=SAMPLE_TDID)],
        )

    assert response.http_meta.response.status_code == 200


@requires_token
def test_deletion_optout_third_party_400_invalid_auth():
    from ttd_data import DataClient, errors
    from ttd_data.models import PartnerDsrDataItem

    with DataClient(server_url=SERVER_URL) as client:
        with pytest.raises(errors.ThirdPartyDsrResponseError) as exc_info:
            client.deletion_opt_out.data_subject_request_third_party_data(
                ttd_auth=INVALID_AUTH_TOKEN,
                data_provider_id=DATA_PROVIDER_ID,
                items=[PartnerDsrDataItem(tdid=SAMPLE_TDID)],
            )

    assert exc_info.value.raw_response.status_code == 400
