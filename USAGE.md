<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from ttd_data import TTDData


with TTDData(
    server_url="https://api.example.com",
) as td_client:

    res = td_client.advertiser.ingest_advertiser_data(advertiser_id="<id>")

    assert res.advertiser_data_server_response is not None

    # Handle response
    print(res.advertiser_data_server_response)
```

</br>

The same SDK client can also be used to make asynchronous requests by importing asyncio.

```python
# Asynchronous Example
import asyncio
from ttd_data import TTDData

async def main():

    async with TTDData(
        server_url="https://api.example.com",
    ) as td_client:

        res = await td_client.advertiser.ingest_advertiser_data_async(advertiser_id="<id>")

        assert res.advertiser_data_server_response is not None

        # Handle response
        print(res.advertiser_data_server_response)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->