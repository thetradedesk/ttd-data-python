# Advertiser

## Overview

### Available Operations

* [ingest_advertiser_data](#ingest_advertiser_data) - Upload first-party data for the specified ID for use in audience targeting.

## ingest_advertiser_data

Upload first-party data for the specified ID for use in audience targeting.

### Example Usage

<!-- UsageSnippet language="python" operationID="IngestAdvertiserData" method="post" path="/data/advertiser" -->
```python
from ttd_data import DataClient


with DataClient(
    server_url="https://api.example.com",
) as data_client:

    res = data_client.advertiser.ingest_advertiser_data(advertiser_id="<id>")

    assert res.advertiser_data_server_response is not None

    # Handle response
    print(res.advertiser_data_server_response)

```

### Parameters

| Parameter                                                                     | Type                                                                          | Required                                                                      | Description                                                                   |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `advertiser_id`                                                               | *str*                                                                         | :heavy_check_mark:                                                            | N/A                                                                           |
| `ttd_auth`                                                                    | *Optional[str]*                                                               | :heavy_minus_sign:                                                            | Data API token for authentication. If not provided, TtdSignature is required. |
| `ttd_signature`                                                               | *Optional[str]*                                                               | :heavy_minus_sign:                                                            | Legacy signature-based authentication. Required if TTD-Auth is not provided.  |
| `data_provider_id`                                                            | *OptionalNullable[str]*                                                       | :heavy_minus_sign:                                                            | N/A                                                                           |
| `items`                                                                       | List[[models.AdvertiserDataItem](../../models/advertiserdataitem.md)]         | :heavy_minus_sign:                                                            | N/A                                                                           |
| `retries`                                                                     | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)              | :heavy_minus_sign:                                                            | Configuration to override the default retry behavior of the client.           |

### Response

**[models.IngestAdvertiserDataResponse](../../models/ingestadvertiserdataresponse.md)**

### Errors

| Error Type                               | Status Code                              | Content Type                             |
| ---------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| errors.AdvertiserDataServerResponseError | 400, 429                                 | application/json                         |
| errors.APIError                          | 4XX, 5XX                                 | \*/\*                                    |