<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from ttd_data import DataClient


with DataClient(
    server_url="https://usw-data.adsrvr.org",
) as data_client:

    res = data_client.advertiser.ingest_advertiser_data(advertiser_id="<id>")

    assert res.advertiser_data_server_response is not None

    # Handle response
    print(res.advertiser_data_server_response)
```

</br>

The same SDK client can also be used to make asynchronous requests by importing asyncio.

```python
# Asynchronous Example
import asyncio
from ttd_data import DataClient

async def main():

    async with DataClient(
        server_url="https://usw-data.adsrvr.org",
    ) as data_client:

        res = await data_client.advertiser.ingest_advertiser_data_async(advertiser_id="<id>")

        assert res.advertiser_data_server_response is not None

        # Handle response
        print(res.advertiser_data_server_response)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->