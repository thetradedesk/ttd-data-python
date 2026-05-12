<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from ttd_data import BaseDataClient


with BaseDataClient() as base_data_client:

    res = base_data_client.advertiser.ingest_advertiser_data(ttd_auth="<value>", advertiser_id="<id>")

    assert res.advertiser_data_server_response is not None

    # Handle response
    print(res.advertiser_data_server_response)
```

</br>

The same SDK client can also be used to make asynchronous requests by importing asyncio.

```python
# Asynchronous Example
import asyncio
from ttd_data import BaseDataClient

async def main():

    async with BaseDataClient() as base_data_client:

        res = await base_data_client.advertiser.ingest_advertiser_data_async(ttd_auth="<value>", advertiser_id="<id>")

        assert res.advertiser_data_server_response is not None

        # Handle response
        print(res.advertiser_data_server_response)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->