from datetime import datetime, timezone
from ttd_data import DataClient
from ttd_data.models import AdvertiserData, AdvertiserDataItem


def _assert_200(resp) -> None:
    assert resp.http_meta is not None
    assert resp.http_meta.response is not None
    assert resp.http_meta.response.status_code == 200


def _data(name: str) -> list[AdvertiserData]:
    return [AdvertiserData(name=name, ttl_in_minutes=43200)]


TS = datetime(2023, 11, 11, 10, 11, 30, tzinfo=timezone.utc)


def test_advertiser_all_id_types(client: DataClient, ttd_auth: str, advertiser_id: str):
    resp = client.advertiser.ingest_advertiser_data(
        ttd_auth=ttd_auth,
        advertiser_id=advertiser_id,
        items=[
            AdvertiserDataItem(
                tdid="123e4567-e89b-12d3-a456-426652340000",
                data=[
                    AdvertiserData(name="1210", timestamp_utc=TS, ttl_in_minutes=43200, base_bid_cpm=5.0, bid_factor=1.5),
                    AdvertiserData(name="1160", ttl_in_minutes=43200),
                ],
            ),
            AdvertiserDataItem(
                daid="a9342d1f-69f1-4bf8-bc2b-1f20eb451f21",
                data=_data("1150"),
            ),
            AdvertiserDataItem(
                uid2="48MjlfIUZpOKNAm9nod7/jCLAXUYsnE1tpVHQSDS0uo=",
                data=_data("1630"),
            ),
            AdvertiserDataItem(
                ramp_id="XY1005wXyWPB1SgpMUKIpzA0I3UaLEz-2lg0wFAr1PWK7FMhs",
                data=_data("1130"),
            ),
            AdvertiserDataItem(
                ramp_id="Xi1005p_iYcKP7ZlvFwwK9EwR8GKl_VJqIWUhEaAFmHLAjNOQ9b6OQzSkA43XiVFcTYQ9X",
                data=[AdvertiserData(name="1170", ttl_in_minutes=43200), AdvertiserData(name="1140", ttl_in_minutes=43200)],
            ),
            AdvertiserDataItem(
                id5="ID5-c62drGF0EC6wsCZVFDbTbZwi33eB0uZTIC8FxJpzsQ",
                data=_data("1800"),
            ),
            AdvertiserDataItem(
                net_id="vp3hsuQk0I8gUEh-Y4gm3R6e8Wm7z8vkWrp_kjlXtKgbIYraTgAmKfm5kbo660gMo2lR4w",
                data=_data("1340"),
            ),
            AdvertiserDataItem(
                first_id="8934d279bba4c7d652a02f624dc334e3",
                data=_data("1810"),
            ),
        ],
    )
    _assert_200(resp)
