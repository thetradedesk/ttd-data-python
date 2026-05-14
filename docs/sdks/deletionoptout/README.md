# DeletionOptOut

## Overview

### Available Operations

* [data_subject_request_advertiser_data](#data_subject_request_advertiser_data) - Delete IDs shared with The Trade Desk for the specified advertiser ID.
* [data_subject_request_merchant_data](#data_subject_request_merchant_data) - Delete IDs shared with The Trade Desk via a product catalog for the specified merchant ID.
* [data_subject_request_third_party_data](#data_subject_request_third_party_data) - Delete IDs shared with The Trade Desk for the specified data provider ID.

## data_subject_request_advertiser_data

Delete IDs shared with The Trade Desk for the specified advertiser ID.

### Example Usage

<!-- UsageSnippet language="python" operationID="DataSubjectRequestAdvertiserData" method="post" path="/data/deletion-optout/advertiser" -->
```python
from ttd_data import BaseDataClientv2


with BaseDataClientv2() as base_data_clientv2:

    res = base_data_clientv2.deletion_opt_out.data_subject_request_advertiser_data(ttd_auth="<value>")

    assert res.advertiser_dsr_response is not None

    # Handle response
    print(res.advertiser_dsr_response)

```

### Parameters

| Parameter                                                                       | Type                                                                            | Required                                                                        | Description                                                                     |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `ttd_auth`                                                                      | *str*                                                                           | :heavy_check_mark:                                                              | Data API token for authentication.                                              |
| `advertiser_id`                                                                 | *OptionalNullable[str]*                                                         | :heavy_minus_sign:                                                              | N/A                                                                             |
| `data_provider_id`                                                              | *OptionalNullable[str]*                                                         | :heavy_minus_sign:                                                              | N/A                                                                             |
| `items`                                                                         | List[[models.BasePartnerDsrDataItem](../../models/basepartnerdsrdataitem.md)]   | :heavy_minus_sign:                                                              | N/A                                                                             |
| `data_load_trace_id`                                                            | *OptionalNullable[str]*                                                         | :heavy_minus_sign:                                                              | N/A                                                                             |
| `request_type`                                                                  | [Optional[models.PartnerDsrRequestType]](../../models/partnerdsrrequesttype.md) | :heavy_minus_sign:                                                              | N/A                                                                             |
| `retries`                                                                       | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                | :heavy_minus_sign:                                                              | Configuration to override the default retry behavior of the client.             |
| `server_url`                                                                    | *Optional[str]*                                                                 | :heavy_minus_sign:                                                              | An optional server URL to use.                                                  |

### Response

**[models.DataSubjectRequestAdvertiserDataResponse](../../models/datasubjectrequestadvertiserdataresponse.md)**

### Errors

| Error Type                        | Status Code                       | Content Type                      |
| --------------------------------- | --------------------------------- | --------------------------------- |
| errors.AdvertiserDsrResponseError | 400, 429                          | application/json                  |
| errors.APIError                   | 4XX, 5XX                          | \*/\*                             |

## data_subject_request_merchant_data

Delete IDs shared with The Trade Desk via a product catalog for the specified merchant ID.

### Example Usage

<!-- UsageSnippet language="python" operationID="DataSubjectRequestMerchantData" method="post" path="/data/deletion-optout/merchant" -->
```python
from ttd_data import BaseDataClientv2


with BaseDataClientv2() as base_data_clientv2:

    res = base_data_clientv2.deletion_opt_out.data_subject_request_merchant_data(ttd_auth="<value>")

    assert res.merchant_dsr_response is not None

    # Handle response
    print(res.merchant_dsr_response)

```

### Parameters

| Parameter                                                                       | Type                                                                            | Required                                                                        | Description                                                                     |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `ttd_auth`                                                                      | *str*                                                                           | :heavy_check_mark:                                                              | Data API token for authentication.                                              |
| `merchant_id`                                                                   | *OptionalNullable[int]*                                                         | :heavy_minus_sign:                                                              | N/A                                                                             |
| `items`                                                                         | List[[models.BasePartnerDsrDataItem](../../models/basepartnerdsrdataitem.md)]   | :heavy_minus_sign:                                                              | N/A                                                                             |
| `data_load_trace_id`                                                            | *OptionalNullable[str]*                                                         | :heavy_minus_sign:                                                              | N/A                                                                             |
| `request_type`                                                                  | [Optional[models.PartnerDsrRequestType]](../../models/partnerdsrrequesttype.md) | :heavy_minus_sign:                                                              | N/A                                                                             |
| `retries`                                                                       | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                | :heavy_minus_sign:                                                              | Configuration to override the default retry behavior of the client.             |
| `server_url`                                                                    | *Optional[str]*                                                                 | :heavy_minus_sign:                                                              | An optional server URL to use.                                                  |

### Response

**[models.DataSubjectRequestMerchantDataResponse](../../models/datasubjectrequestmerchantdataresponse.md)**

### Errors

| Error Type                      | Status Code                     | Content Type                    |
| ------------------------------- | ------------------------------- | ------------------------------- |
| errors.MerchantDsrResponseError | 400, 429                        | application/json                |
| errors.APIError                 | 4XX, 5XX                        | \*/\*                           |

## data_subject_request_third_party_data

Delete IDs shared with The Trade Desk for the specified data provider ID.

### Example Usage

<!-- UsageSnippet language="python" operationID="DataSubjectRequestThirdPartyData" method="post" path="/data/deletion-optout/thirdparty" -->
```python
from ttd_data import BaseDataClientv2


with BaseDataClientv2() as base_data_clientv2:

    res = base_data_clientv2.deletion_opt_out.data_subject_request_third_party_data(ttd_auth="<value>")

    assert res.third_party_dsr_response is not None

    # Handle response
    print(res.third_party_dsr_response)

```

### Parameters

| Parameter                                                                       | Type                                                                            | Required                                                                        | Description                                                                     |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `ttd_auth`                                                                      | *str*                                                                           | :heavy_check_mark:                                                              | Data API token for authentication.                                              |
| `data_provider_id`                                                              | *OptionalNullable[str]*                                                         | :heavy_minus_sign:                                                              | N/A                                                                             |
| `brand_id`                                                                      | *OptionalNullable[str]*                                                         | :heavy_minus_sign:                                                              | N/A                                                                             |
| `items`                                                                         | List[[models.BasePartnerDsrDataItem](../../models/basepartnerdsrdataitem.md)]   | :heavy_minus_sign:                                                              | N/A                                                                             |
| `data_load_trace_id`                                                            | *OptionalNullable[str]*                                                         | :heavy_minus_sign:                                                              | N/A                                                                             |
| `request_type`                                                                  | [Optional[models.PartnerDsrRequestType]](../../models/partnerdsrrequesttype.md) | :heavy_minus_sign:                                                              | N/A                                                                             |
| `retries`                                                                       | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                | :heavy_minus_sign:                                                              | Configuration to override the default retry behavior of the client.             |
| `server_url`                                                                    | *Optional[str]*                                                                 | :heavy_minus_sign:                                                              | An optional server URL to use.                                                  |

### Response

**[models.DataSubjectRequestThirdPartyDataResponse](../../models/datasubjectrequestthirdpartydataresponse.md)**

### Errors

| Error Type                        | Status Code                       | Content Type                      |
| --------------------------------- | --------------------------------- | --------------------------------- |
| errors.ThirdPartyDsrResponseError | 400, 429                          | application/json                  |
| errors.APIError                   | 4XX, 5XX                          | \*/\*                             |