import os
import pytest
from ttd_data import DataClient


@pytest.fixture(scope="session")
def ttd_auth() -> str:
    token = os.environ.get("TTD_AUTH_TOKEN")
    if not token:
        pytest.skip("TTD_AUTH_TOKEN not set")
    return token


@pytest.fixture(scope="session")
def advertiser_id() -> str:
    aid = os.environ.get("TEST_ADVERTISER_ID")
    if not aid:
        pytest.skip("TEST_ADVERTISER_ID not set")
    return aid


@pytest.fixture(scope="session")
def data_provider_id() -> str:
    dpid = os.environ.get("TEST_DATA_PROVIDER_ID")
    if not dpid:
        pytest.skip("TEST_DATA_PROVIDER_ID not set")
    return dpid


@pytest.fixture(scope="session")
def merchant_id() -> int:
    mid = os.environ.get("TEST_MERCHANT_ID")
    if not mid:
        pytest.skip("TEST_MERCHANT_ID not set")
    return int(mid)


@pytest.fixture(scope="session")
def tracking_tag_id() -> str:
    ttid = os.environ.get("TEST_TRACKING_TAG_ID")
    if not ttid:
        pytest.skip("TEST_TRACKING_TAG_ID not set")
    return ttid


@pytest.fixture(scope="session")
def client() -> DataClient:
    server_url = os.environ.get("TTD_DATA_SERVER_URL", "https://usw-data.adsrvr.org/")
    return DataClient(server_url=server_url)
