from ttd_data import DataClient
from ttd_data.models import ThirdPartyData, ThirdPartyDataItem


def _assert_200(resp) -> None:
    assert resp.http_meta is not None
    assert resp.http_meta.response is not None
    assert resp.http_meta.response.status_code == 200


def _data(name: str) -> list[ThirdPartyData]:
    return [ThirdPartyData(name=name)]


def test_third_party_all_id_types(client: DataClient, ttd_auth: str, data_provider_id: str):
    resp = client.third_party.ingest_third_party_data(
        ttd_auth=ttd_auth,
        data_provider_id=data_provider_id,
        items=[
            ThirdPartyDataItem(tdid="123e4567-e89b-12d3-a456-426652340000", data=_data("1210")),
            ThirdPartyDataItem(daid="a9342d1f-69f1-4bf8-bc2b-1f20eb451f21", data=_data("1150")),
            ThirdPartyDataItem(uid2="48MjlfIUZpOKNAm9nod7/jCLAXUYsnE1tpVHQSDS0uo=", data=_data("1630")),
            ThirdPartyDataItem(ramp_id="XY1005wXyWPB1SgpMUKIpzA0I3UaLEz-2lg0wFAr1PWK7FMhs", data=_data("1130")),
            ThirdPartyDataItem(
                ramp_id="Xi1005p_iYcKP7ZlvFwwK9EwR8GKl_VJqIWUhEaAFmHLAjNOQ9b6OQzSkA43XiVFcTYQ9X",
                data=[ThirdPartyData(name="1170"), ThirdPartyData(name="1140")],
            ),
            ThirdPartyDataItem(id5="ID5-c62drGF0EC6wsCZVFDbTbZwi33eB0uZTIC8FxJpzsQ", data=_data("1800")),
            ThirdPartyDataItem(
                net_id="vp3hsuQk0I8gUEh-Y4gm3R6e8Wm7z8vkWrp_kjlXtKgbIYraTgAmKfm5kbo660gMo2lR4w",
                data=_data("1340"),
            ),
            ThirdPartyDataItem(first_id="8934d279bba4c7d652a02f624dc334e3", data=_data("1810")),
        ],
    )
    _assert_200(resp)
