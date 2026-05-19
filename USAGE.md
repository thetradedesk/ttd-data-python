<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example — pre-resolved identifier, no UID2 config needed
from ttd_data import DataClient
from ttd_data.models import AdvertiserData, AdvertiserDataItem

with DataClient(server_url="<TTD_DATA_SERVER_URL>") as client:
    response = client.advertiser.ingest_advertiser_data(
        ttd_auth="<TTD_AUTH_TOKEN>",
        advertiser_id="<ADVERTISER_ID>",
        items=[
            AdvertiserDataItem(
                data=[AdvertiserData(name="loyalty_members")],
                tdid="<TDID>",
            )
        ],
    )
    print(response.advertiser_data_server_response)
```

</br>

```python
# Synchronous Example — with UID2 identity mapping (raw email resolved before ingest)
from ttd_data import DataClient, IdentityScope, UID2Config, UID2ServiceError
from ttd_data.models import AdvertiserData, AdvertiserDataItem

uid2_config = UID2Config(
    base_url="<UID2_BASE_URL>",
    api_key="<UID2_API_KEY>",
    client_secret="<UID2_CLIENT_SECRET>",
    identity_scope=IdentityScope.UID2,
)

try:
    with DataClient(uid2_config=uid2_config, server_url="<TTD_DATA_SERVER_URL>") as client:
        response = client.advertiser.ingest_advertiser_data(
            ttd_auth="<TTD_AUTH_TOKEN>",
            advertiser_id="<ADVERTISER_ID>",
            items=[
                AdvertiserDataItem(
                    data=[AdvertiserData(name="loyalty_members")],
                    email="user@example.com",
                )
            ],
        )
        print(response.advertiser_data_server_response)
except UID2ServiceError as e:
    print(f"UID2 service error: {e}")
```

</br>

The same SDK client can also be used to make asynchronous requests by importing asyncio.

```python
# Asynchronous Example — pre-resolved identifier, no UID2 config needed
import asyncio
from ttd_data import DataClient
from ttd_data.models import AdvertiserData, AdvertiserDataItem

async def main():
    async with DataClient(server_url="<TTD_DATA_SERVER_URL>") as client:
        response = await client.advertiser.ingest_advertiser_data_async(
            ttd_auth="<TTD_AUTH_TOKEN>",
            advertiser_id="<ADVERTISER_ID>",
            items=[
                AdvertiserDataItem(
                    data=[AdvertiserData(name="loyalty_members")],
                    tdid="<TDID>",
                )
            ],
        )
        print(response.advertiser_data_server_response)

asyncio.run(main())
```

</br>

```python
# Asynchronous Example — with UID2 identity mapping (raw email resolved before ingest)
import asyncio
from ttd_data import DataClient, IdentityScope, UID2Config, UID2ServiceError
from ttd_data.models import AdvertiserData, AdvertiserDataItem

uid2_config = UID2Config(
    base_url="<UID2_BASE_URL>",
    api_key="<UID2_API_KEY>",
    client_secret="<UID2_CLIENT_SECRET>",
    identity_scope=IdentityScope.UID2,
)

async def main():
    try:
        async with DataClient(uid2_config=uid2_config, server_url="<TTD_DATA_SERVER_URL>") as client:
            response = await client.advertiser.ingest_advertiser_data_async(
                ttd_auth="<TTD_AUTH_TOKEN>",
                advertiser_id="<ADVERTISER_ID>",
                items=[
                    AdvertiserDataItem(
                        data=[AdvertiserData(name="loyalty_members")],
                        email="user@example.com",
                    )
                ],
            )
            print(response.advertiser_data_server_response)
    except UID2ServiceError as e:
        print(f"UID2 service error: {e}")

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->
