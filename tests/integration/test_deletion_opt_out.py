from ttd_data import DataClient
from ttd_data.models import PartnerDsrDataItem, PartnerDsrRequestType


def _assert_200(resp) -> None:
    assert resp.http_meta is not None
    assert resp.http_meta.response is not None
    assert resp.http_meta.response.status_code == 200


ITEMS = [
    PartnerDsrDataItem(tdid="123e4567-e89b-12d3-a456-426652340000"),
    PartnerDsrDataItem(daid="a9342d1f-69f1-4bf8-bc2b-1f20eb451f21"),
    PartnerDsrDataItem(uid2="48MjlfIUZpOKNAm9nod7/jCLAXUYsnE1tpVHQSDS0uo="),
    PartnerDsrDataItem(ramp_id="XY1005wXyWPB1SgpMUKIpzA0I3UaLEz-2lg0wFAr1PWK7FMhs"),
    PartnerDsrDataItem(id5="ID5-c62drGF0EC6wsCZVFDbTbZwi33eB0uZTIC8FxJpzsQ"),
    PartnerDsrDataItem(net_id="vp3hsuQk0I8gUEh-Y4gm3R6e8Wm7z8vkWrp_kjlXtKgbIYraTgAmKfm5kbo660gMo2lR4w"),
    PartnerDsrDataItem(first_id="8934d279bba4c7d652a02f624dc334e3"),
]


def test_deletion_optout_advertiser_all_id_types(
    client: DataClient, ttd_auth: str, advertiser_id: str
):
    resp = client.deletion_opt_out.data_subject_request_advertiser_data(
        ttd_auth=ttd_auth,
        advertiser_id=advertiser_id,
        request_type=PartnerDsrRequestType.OPT_OUT,
        items=ITEMS,
    )
    _assert_200(resp)


def test_deletion_optout_third_party_all_id_types(
    client: DataClient, ttd_auth: str, data_provider_id: str
):
    resp = client.deletion_opt_out.data_subject_request_third_party_data(
        ttd_auth=ttd_auth,
        data_provider_id=data_provider_id,
        request_type=PartnerDsrRequestType.OPT_OUT,
        items=ITEMS,
    )
    _assert_200(resp)


def test_deletion_optout_merchant_all_id_types(
    client: DataClient, ttd_auth: str, merchant_id: int
):
    resp = client.deletion_opt_out.data_subject_request_merchant_data(
        ttd_auth=ttd_auth,
        merchant_id=merchant_id,
        request_type=PartnerDsrRequestType.OPT_OUT,
        items=ITEMS,
    )
    _assert_200(resp)
