# IngestAdvertiserDataRequest


## Fields

| Field                                                                         | Type                                                                          | Required                                                                      | Description                                                                   |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `ttd_auth`                                                                    | *Optional[str]*                                                               | :heavy_minus_sign:                                                            | Data API token for authentication. If not provided, TtdSignature is required. |
| `ttd_signature`                                                               | *Optional[str]*                                                               | :heavy_minus_sign:                                                            | Legacy signature-based authentication. Required if TTD-Auth is not provided.  |
| `body`                                                                        | [models.AdvertiserDataRequest](../models/advertiserdatarequest.md)            | :heavy_check_mark:                                                            | N/A                                                                           |