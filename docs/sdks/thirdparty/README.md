# ThirdParty

## Overview

### Available Operations

* [ingest_third_party_data](#ingest_third_party_data) - Upload third-party data for the specified data provider for use in audience targeting.

## ingest_third_party_data

Upload third-party data for the specified data provider for use in audience targeting.

### Example Usage

<!-- UsageSnippet language="python" operationID="IngestThirdPartyData" method="post" path="/data/thirdparty" -->
```python
from ttd_data import BaseDataClient


with BaseDataClient() as base_data_client:

    res = base_data_client.third_party.ingest_third_party_data(ttd_auth="<value>", data_provider_id="<id>", is_user_id_already_hashed=False)

    assert res.third_party_data_server_response is not None

    # Handle response
    print(res.third_party_data_server_response)

```

### Parameters

| Parameter                                                                     | Type                                                                          | Required                                                                      | Description                                                                   |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `ttd_auth`                                                                    | *str*                                                                         | :heavy_check_mark:                                                            | Data API token for authentication.                                            |
| `data_provider_id`                                                            | *str*                                                                         | :heavy_check_mark:                                                            | N/A                                                                           |
| `items`                                                                       | List[[models.BaseThirdPartyDataItem](../../models/basethirdpartydataitem.md)] | :heavy_minus_sign:                                                            | N/A                                                                           |
| `data_load_trace_id`                                                          | *OptionalNullable[str]*                                                       | :heavy_minus_sign:                                                            | N/A                                                                           |
| `is_user_id_already_hashed`                                                   | *Optional[bool]*                                                              | :heavy_minus_sign:                                                            | N/A                                                                           |
| `data_origins`                                                                | List[[models.DataOrigin](../../models/dataorigin.md)]                         | :heavy_minus_sign:                                                            | N/A                                                                           |
| `retries`                                                                     | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)              | :heavy_minus_sign:                                                            | Configuration to override the default retry behavior of the client.           |
| `server_url`                                                                  | *Optional[str]*                                                               | :heavy_minus_sign:                                                            | An optional server URL to use.                                                |

### Response

**[models.IngestThirdPartyDataResponse](../../models/ingestthirdpartydataresponse.md)**

### Errors

| Error Type                               | Status Code                              | Content Type                             |
| ---------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| errors.ThirdPartyDataServerResponseError | 400, 429                                 | application/json                         |
| errors.APIError                          | 4XX, 5XX                                 | \*/\*                                    |