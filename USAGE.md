<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from ttd_data_python import Ttddata


with Ttddata(
    server_url="https://api.example.com",
) as ttddata:

    res = ttddata.advertiser.ingest_advertiser_data(advertiser_id="<id>")

    # Handle response
    print(res)
```

</br>

The same SDK client can also be used to make asynchronous requests by importing asyncio.

```python
# Asynchronous Example
import asyncio
from ttd_data_python import Ttddata

async def main():

    async with Ttddata(
        server_url="https://api.example.com",
    ) as ttddata:

        res = await ttddata.advertiser.ingest_advertiser_data_async(advertiser_id="<id>")

        # Handle response
        print(res)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->