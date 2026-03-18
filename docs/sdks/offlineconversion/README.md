# OfflineConversion

## Overview

### Available Operations

* [ingest_offline_conversion_data](#ingest_offline_conversion_data) - Upload offline conversion data for the specified data provider.

## ingest_offline_conversion_data

Upload offline conversion data for the specified data provider.

### Example Usage

<!-- UsageSnippet language="python" operationID="IngestOfflineConversionData" method="post" path="/providerapi/offlineconversion" -->
```python
from ttd_data import DataClient


with DataClient() as data_client:

    res = data_client.offline_conversion.ingest_offline_conversion_data(ttd_auth="<value>", data_provider_id="<id>")

    assert res.offline_conversion_data_server_response is not None

    # Handle response
    print(res.offline_conversion_data_server_response)

```

### Parameters

| Parameter                                                                           | Type                                                                                | Required                                                                            | Description                                                                         |
| ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `ttd_auth`                                                                          | *str*                                                                               | :heavy_check_mark:                                                                  | Data API token for authentication.                                                  |
| `data_provider_id`                                                                  | *str*                                                                               | :heavy_check_mark:                                                                  | N/A                                                                                 |
| `user_id_array_metadata_format`                                                     | List[*str*]                                                                         | :heavy_minus_sign:                                                                  | N/A                                                                                 |
| `items`                                                                             | List[[models.OfflineConversionDataItem](../../models/offlineconversiondataitem.md)] | :heavy_minus_sign:                                                                  | N/A                                                                                 |
| `data_load_trace_id`                                                                | *OptionalNullable[str]*                                                             | :heavy_minus_sign:                                                                  | N/A                                                                                 |
| `data_origins`                                                                      | List[[models.DataOrigin](../../models/dataorigin.md)]                               | :heavy_minus_sign:                                                                  | N/A                                                                                 |
| `retries`                                                                           | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                    | :heavy_minus_sign:                                                                  | Configuration to override the default retry behavior of the client.                 |
| `server_url`                                                                        | *Optional[str]*                                                                     | :heavy_minus_sign:                                                                  | An optional server URL to use.                                                      |

### Response

**[models.IngestOfflineConversionDataResponse](../../models/ingestofflineconversiondataresponse.md)**

### Errors

| Error Type                                      | Status Code                                     | Content Type                                    |
| ----------------------------------------------- | ----------------------------------------------- | ----------------------------------------------- |
| errors.OfflineConversionDataServerResponseError | 400, 429                                        | application/json                                |
| errors.APIError                                 | 4XX, 5XX                                        | \*/\*                                           |