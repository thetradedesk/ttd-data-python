# Advertiser

## Overview

### Available Operations

* [ingest_advertiser_data](#ingest_advertiser_data) - Upload first-party data for the specified ID for use in audience targeting.

## ingest_advertiser_data

Upload first-party data for the specified ID for use in audience targeting.

### Example Usage

<!-- UsageSnippet language="python" operationID="IngestAdvertiserData" method="post" path="/data/advertiser" -->
```python
from ttd_data import BaseDataClient


with BaseDataClient() as base_data_client:

    res = base_data_client.advertiser.ingest_advertiser_data(ttd_auth="<value>", advertiser_id="<id>")

    assert res.advertiser_data_server_response is not None

    # Handle response
    print(res.advertiser_data_server_response)

```

### Parameters

| Parameter                                                                     | Type                                                                          | Required                                                                      | Description                                                                   |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `ttd_auth`                                                                    | *str*                                                                         | :heavy_check_mark:                                                            | Data API token for authentication.                                            |
| `advertiser_id`                                                               | *str*                                                                         | :heavy_check_mark:                                                            | N/A                                                                           |
| `data_provider_id`                                                            | *OptionalNullable[str]*                                                       | :heavy_minus_sign:                                                            | N/A                                                                           |
| `items`                                                                       | List[[models.BaseAdvertiserDataItem](../../models/baseadvertiserdataitem.md)] | :heavy_minus_sign:                                                            | N/A                                                                           |
| `data_load_trace_id`                                                          | *OptionalNullable[str]*                                                       | :heavy_minus_sign:                                                            | N/A                                                                           |
| `data_origins`                                                                | List[[models.DataOrigin](../../models/dataorigin.md)]                         | :heavy_minus_sign:                                                            | N/A                                                                           |
| `retries`                                                                     | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)              | :heavy_minus_sign:                                                            | Configuration to override the default retry behavior of the client.           |
| `server_url`                                                                  | *Optional[str]*                                                               | :heavy_minus_sign:                                                            | An optional server URL to use.                                                |

### Response

**[models.IngestAdvertiserDataResponse](../../models/ingestadvertiserdataresponse.md)**

### Errors

| Error Type                               | Status Code                              | Content Type                             |
| ---------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| errors.AdvertiserDataServerResponseError | 400, 429                                 | application/json                         |
| errors.APIError                          | 4XX, 5XX                                 | \*/\*                                    |