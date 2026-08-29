from datetime import datetime, timezone
from ttd_data import DataClient
from ttd_data.models import OfflineConversionDataItem


def _assert_200(resp) -> None:
    assert resp.http_meta is not None
    assert resp.http_meta.response is not None
    assert resp.http_meta.response.status_code == 200


TS = datetime(2023, 11, 11, 10, 11, 30, tzinfo=timezone.utc)


def test_offline_conversion_all_id_types(
    client: DataClient, ttd_auth: str, data_provider_id: str, tracking_tag_id: str
):
    resp = client.offline_conversion.ingest_offline_conversion_data(
        ttd_auth=ttd_auth,
        data_provider_id=data_provider_id,
        items=[
            OfflineConversionDataItem(
                tracking_tag_id=tracking_tag_id,
                timestamp_utc=TS,
                tdid="123e4567-e89b-12d3-a456-426652340000",
            ),
            OfflineConversionDataItem(
                tracking_tag_id=tracking_tag_id,
                timestamp_utc=TS,
                daid="a9342d1f-69f1-4bf8-bc2b-1f20eb451f21",
            ),
            OfflineConversionDataItem(
                tracking_tag_id=tracking_tag_id,
                timestamp_utc=TS,
                uid2="48MjlfIUZpOKNAm9nod7/jCLAXUYsnE1tpVHQSDS0uo=",
            ),
            OfflineConversionDataItem(
                tracking_tag_id=tracking_tag_id,
                timestamp_utc=TS,
                ramp_id="XY1005wXyWPB1SgpMUKIpzA0I3UaLEz-2lg0wFAr1PWK7FMhs",
            ),
        ],
    )
    _assert_200(resp)
