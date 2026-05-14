<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from ttd_data import BaseDataClientv2


with BaseDataClientv2() as base_data_clientv2:

    res = base_data_clientv2.advertiser.ingest_advertiser_data(ttd_auth="<value>", advertiser_id="<id>")

    assert res.advertiser_data_server_response is not None

    # Handle response
    print(res.advertiser_data_server_response)
```

</br>

The same SDK client can also be used to make asynchronous requests by importing asyncio.

```python
# Asynchronous Example
import asyncio
from ttd_data import BaseDataClientv2

async def main():

    async with BaseDataClientv2() as base_data_clientv2:

        res = await base_data_clientv2.advertiser.ingest_advertiser_data_async(ttd_auth="<value>", advertiser_id="<id>")

        assert res.advertiser_data_server_response is not None

        # Handle response
        print(res.advertiser_data_server_response)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->