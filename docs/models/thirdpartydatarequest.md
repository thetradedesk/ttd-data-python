# ThirdPartyDataRequest


## Fields

| Field                                                              | Type                                                               | Required                                                           | Description                                                        |
| ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| `data_provider_id`                                                 | *str*                                                              | :heavy_check_mark:                                                 | N/A                                                                |
| `items`                                                            | List[[models.ThirdPartyDataItem](../models/thirdpartydataitem.md)] | :heavy_minus_sign:                                                 | N/A                                                                |
| `data_load_trace_id`                                               | *OptionalNullable[str]*                                            | :heavy_minus_sign:                                                 | N/A                                                                |
| `is_user_id_already_hashed`                                        | *Optional[bool]*                                                   | :heavy_minus_sign:                                                 | N/A                                                                |
| `data_origins`                                                     | List[[models.DataOrigin](../models/dataorigin.md)]                 | :heavy_minus_sign:                                                 | N/A                                                                |