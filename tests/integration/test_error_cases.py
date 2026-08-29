"""
Error-case integration tests derived from adplatform DataServer source code.

400 sources (AdvertiserDataHandler.cs / UserPermissionValidator.cs):
  - Bad/invalid TTD-Auth token (authentication failure)
  - Empty Items list ("Items attribute must be a non-empty list.")

403 sources (UserPermissionValidator.cs):
  - Token does not have permission for the given AdvertiserId
  - Token does not have permission for the given DataProviderId
  Requires env vars: TEST_WRONG_ADVERTISER_ID, TEST_WRONG_DATA_PROVIDER_ID
  (a real TTD ID that exists in the system but is not owned by the test token)

413 sources (AdvertiserDataHandler.cs line 242):
  - Request body > ProvisionalMaxRequestSizeBytes (4 MB)
  Gated by AllowLargeSizeRequest feature switch (enabled=true by default,
  meaning the check is SKIPPED in standard environments). Included here for
  completeness; the test is skipped unless TEST_413_ENABLED=1 is set.
"""
import os
import pytest
from datetime import datetime, timezone
from ttd_data import DataClient
from ttd_data.models import (
    AdvertiserData,
    AdvertiserDataItem,
    ThirdPartyData,
    ThirdPartyDataItem,
    OfflineConversionDataItem,
    PartnerDsrDataItem,
    PartnerDsrRequestType,
)
from ttd_data import errors


BAD_TOKEN = "not-a-valid-auth-token"
TDID = "123e4567-e89b-12d3-a456-426652340000"
TS = datetime(2023, 11, 11, 10, 11, 30, tzinfo=timezone.utc)


# ── per-file fixtures (skip if env vars missing) ─────────────────────────────

@pytest.fixture(scope="module")
def wrong_advertiser_id():
    waid = os.environ.get("TEST_WRONG_ADVERTISER_ID")
    if not waid:
        pytest.skip("TEST_WRONG_ADVERTISER_ID not set")
    return waid


@pytest.fixture(scope="module")
def wrong_data_provider_id():
    wdpid = os.environ.get("TEST_WRONG_DATA_PROVIDER_ID")
    if not wdpid:
        pytest.skip("TEST_WRONG_DATA_PROVIDER_ID not set")
    return wdpid


# ── helpers ───────────────────────────────────────────────────────────────────

def _adv_items():
    return [AdvertiserDataItem(tdid=TDID, data=[AdvertiserData(name="seg", ttl_in_minutes=43200)])]

def _3pd_items():
    return [ThirdPartyDataItem(tdid=TDID, data=[ThirdPartyData(name="seg")])]


# ── 400: bad auth token ───────────────────────────────────────────────────────

def test_advertiser_bad_token_400(client: DataClient, advertiser_id: str):
    with pytest.raises(errors.AdvertiserDataServerResponseError) as exc:
        client.advertiser.ingest_advertiser_data(
            ttd_auth=BAD_TOKEN,
            advertiser_id=advertiser_id,
            items=_adv_items(),
        )
    assert exc.value.status_code == 400


def test_third_party_bad_token_400(client: DataClient, data_provider_id: str):
    with pytest.raises(errors.ThirdPartyDataServerResponseError) as exc:
        client.third_party.ingest_third_party_data(
            ttd_auth=BAD_TOKEN,
            data_provider_id=data_provider_id,
            items=_3pd_items(),
        )
    assert exc.value.status_code == 400


def test_offline_conversion_bad_token_400(client: DataClient, data_provider_id: str, tracking_tag_id: str):
    with pytest.raises(errors.OfflineConversionDataServerResponseError) as exc:
        client.offline_conversion.ingest_offline_conversion_data(
            ttd_auth=BAD_TOKEN,
            data_provider_id=data_provider_id,
            items=[OfflineConversionDataItem(tracking_tag_id=tracking_tag_id, timestamp_utc=TS, tdid=TDID)],
        )
    assert exc.value.status_code == 400


def test_dsr_advertiser_bad_token_400(client: DataClient, advertiser_id: str):
    with pytest.raises(errors.AdvertiserDsrResponseError) as exc:
        client.deletion_opt_out.data_subject_request_advertiser_data(
            ttd_auth=BAD_TOKEN,
            advertiser_id=advertiser_id,
            request_type=PartnerDsrRequestType.OPT_OUT,
            items=[PartnerDsrDataItem(tdid=TDID)],
        )
    assert exc.value.status_code == 400


def test_dsr_third_party_bad_token_400(client: DataClient, data_provider_id: str):
    with pytest.raises(errors.ThirdPartyDsrResponseError) as exc:
        client.deletion_opt_out.data_subject_request_third_party_data(
            ttd_auth=BAD_TOKEN,
            data_provider_id=data_provider_id,
            request_type=PartnerDsrRequestType.OPT_OUT,
            items=[PartnerDsrDataItem(tdid=TDID)],
        )
    assert exc.value.status_code == 400


# ── 400: empty items ──────────────────────────────────────────────────────────

def test_advertiser_empty_items_400(client: DataClient, ttd_auth: str, advertiser_id: str):
    with pytest.raises(errors.AdvertiserDataServerResponseError) as exc:
        client.advertiser.ingest_advertiser_data(
            ttd_auth=ttd_auth,
            advertiser_id=advertiser_id,
            items=[],
        )
    assert exc.value.status_code == 400


def test_third_party_empty_items_400(client: DataClient, ttd_auth: str, data_provider_id: str):
    with pytest.raises(errors.ThirdPartyDataServerResponseError) as exc:
        client.third_party.ingest_third_party_data(
            ttd_auth=ttd_auth,
            data_provider_id=data_provider_id,
            items=[],
        )
    assert exc.value.status_code == 400


def test_offline_conversion_empty_items_400(client: DataClient, ttd_auth: str, data_provider_id: str):
    with pytest.raises(errors.OfflineConversionDataServerResponseError) as exc:
        client.offline_conversion.ingest_offline_conversion_data(
            ttd_auth=ttd_auth,
            data_provider_id=data_provider_id,
            items=[],
        )
    assert exc.value.status_code == 400


# ── 403: token not authorized for advertiser / data provider ──────────────────

def test_advertiser_wrong_advertiser_403(
    client: DataClient, ttd_auth: str, wrong_advertiser_id: str
):
    with pytest.raises(errors.APIError) as exc:
        client.advertiser.ingest_advertiser_data(
            ttd_auth=ttd_auth,
            advertiser_id=wrong_advertiser_id,
            items=_adv_items(),
        )
    assert exc.value.status_code == 403


def test_third_party_wrong_provider_403(
    client: DataClient, ttd_auth: str, wrong_data_provider_id: str
):
    with pytest.raises(errors.APIError) as exc:
        client.third_party.ingest_third_party_data(
            ttd_auth=ttd_auth,
            data_provider_id=wrong_data_provider_id,
            items=_3pd_items(),
        )
    assert exc.value.status_code == 403


def test_dsr_advertiser_wrong_advertiser_403(
    client: DataClient, ttd_auth: str, wrong_advertiser_id: str
):
    with pytest.raises(errors.APIError) as exc:
        client.deletion_opt_out.data_subject_request_advertiser_data(
            ttd_auth=ttd_auth,
            advertiser_id=wrong_advertiser_id,
            request_type=PartnerDsrRequestType.OPT_OUT,
            items=[PartnerDsrDataItem(tdid=TDID)],
        )
    assert exc.value.status_code == 403


# ── 413: oversized request ────────────────────────────────────────────────────
# The server-side check is gated by AllowLargeSizeRequest feature switch
# (enabled=True by default, which SKIPS the check). This test is only run
# when TEST_413_ENABLED=1 to avoid false negatives in standard environments.

@pytest.mark.skipif(
    os.environ.get("TEST_413_ENABLED") != "1",
    reason="413 check is bypassed by AllowLargeSizeRequest feature switch unless TEST_413_ENABLED=1",
)
def test_advertiser_oversized_body_413(client: DataClient, ttd_auth: str, advertiser_id: str):
    # ~250 bytes per item × 20,000 items ≈ 5 MB → exceeds 4 MB limit
    large_items = [
        AdvertiserDataItem(
            tdid=f"00000000-0000-0000-0000-{str(i).zfill(12)}",
            data=[AdvertiserData(name="x" * 200, ttl_in_minutes=43200)],
        )
        for i in range(20_000)
    ]
    with pytest.raises(errors.APIError) as exc:
        client.advertiser.ingest_advertiser_data(
            ttd_auth=ttd_auth,
            advertiser_id=advertiser_id,
            items=large_items,
        )
    assert exc.value.status_code == 413
