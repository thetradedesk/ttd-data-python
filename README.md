# ttd-data

Developer-friendly & type-safe Python SDK specifically catered to leverage *ttd-data* API.

[![Built by Speakeasy](https://img.shields.io/badge/Built_by-SPEAKEASY-374151?style=for-the-badge&labelColor=f3f4f6)](https://www.speakeasy.com/?utm_source=ttd-data&utm_campaign=python)
[![License: Apache-2.0](https://img.shields.io/badge/LICENSE_//_Apache--2.0-3b5bdb?style=for-the-badge&labelColor=eff6ff)](https://www.apache.org/licenses/LICENSE-2.0)




<!-- Start Summary [summary] -->
## Summary

TTD Data API: Python SDK for The Trade Desk Data API. Provides operations for ingesting advertiser data,
third-party data, and offline conversions, as well as handling data subject deletion and opt-out requests.

For more information, see the official API documentation:
- [Advertiser targeting data (1PD)](https://open.thetradedesk.com/advertiser/docsApp/GuidesAdvertiser/data/doc/post-data-advertiser-firstparty)
- [Third-party targeting data (3PD)](https://open.thetradedesk.com/provider/docsApp/GuidesProvider/audience/doc/post-data-thirdparty)
- [Offline conversions (CAPI)](https://open.thetradedesk.com/advertiser/docsApp/GuidesAdvertiser/data/doc/post-providerapi-offlineconversion)

Deletions and opt-outs:
- [Advertiser](https://open.thetradedesk.com/advertiser/docsApp/GuidesAdvertiser/data/doc/post-data-deletion-optout-advertiser)
- [Third party](https://open.thetradedesk.com/provider/docsApp/GuidesProvider/audience/doc/post-data-deletion-optout-thirdparty)
- [Merchant](https://open.thetradedesk.com/provider/docsApp/GuidesProvider/retail/doc/post-data-deletion-optout-merchant)
<!-- End Summary [summary] -->

<!-- Start Table of Contents [toc] -->
## Table of Contents
<!-- $toc-max-depth=2 -->
* [ttd-data](#ttd-data)
  * [SDK Installation](#sdk-installation)
  * [IDE Support](#ide-support)
  * [SDK Example Usage](#sdk-example-usage)
  * [Available Resources and Operations](#available-resources-and-operations)
  * [Retries](#retries)
  * [Error Handling](#error-handling)
  * [Custom HTTP Client](#custom-http-client)
  * [Resource Management](#resource-management)
  * [Debugging](#debugging)
* [Development](#development)
  * [Maturity](#maturity)
  * [Contributions](#contributions)

<!-- End Table of Contents [toc] -->

<!-- Start SDK Installation [installation] -->
## SDK Installation

> [!NOTE]
> **Python version upgrade policy**
>
> Once a Python version reaches its [official end of life date](https://devguide.python.org/versions/), a 3-month grace period is provided for users to upgrade. Following this grace period, the minimum python version supported in the SDK will be updated.

The SDK can be installed with *uv*, *pip*, or *poetry* package managers.

### uv

*uv* is a fast Python package installer and resolver, designed as a drop-in replacement for pip and pip-tools. It's recommended for its speed and modern Python tooling capabilities.

```bash
uv add ttd-data
```

### PIP

*PIP* is the default package installer for Python, enabling easy installation and management of packages from PyPI via the command line.

```bash
pip install ttd-data
```

### Poetry

*Poetry* is a modern tool that simplifies dependency management and package publishing by using a single `pyproject.toml` file to handle project metadata and dependencies.

```bash
poetry add ttd-data
```

### Shell and script usage with `uv`

You can use this SDK in a Python shell with [uv](https://docs.astral.sh/uv/) and the `uvx` command that comes with it like so:

```shell
uvx --from ttd-data python
```

It's also possible to write a standalone Python script without needing to set up a whole project like so:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ttd-data",
# ]
# ///

from ttd_data import BaseDataClient

sdk = BaseDataClient(
  # SDK arguments
)

# Rest of script here...
```

Once that is saved to a file, you can run it with `uv run script.py` where
`script.py` can be replaced with the actual file name.
<!-- End SDK Installation [installation] -->

<!-- Start IDE Support [idesupport] -->
## IDE Support

### PyCharm

Generally, the SDK will work well with most IDEs out of the box. However, when using PyCharm, you can enjoy much better integration with Pydantic by installing an additional plugin.

- [PyCharm Pydantic Plugin](https://docs.pydantic.dev/latest/integrations/pycharm/)
<!-- End IDE Support [idesupport] -->

## SDK Example Usage

### 1. Advertiser targeting Data (1PD)

```python
from ttd_data import DataClient, models

with DataClient() as client:
    response = client.advertiser.ingest_advertiser_data(
        ttd_auth=TTD_AUTH_TOKEN,
        advertiser_id=ADVERTISER_ID,
        items=[
            models.AdvertiserDataItem(
                tdid="<TDID>",
                data=[
                    models.AdvertiserData(name="loyalty_members"),
                ],
            )
        ],
    )

```

### 2. Third Party Targeting Data (3PD)

```python
from ttd_data import DataClient, models

with DataClient() as client:
    response = client.third_party.ingest_third_party_data(
        ttd_auth=TTD_AUTH_TOKEN,
        data_provider_id=DATA_PROVIDER_ID,
        items=[
            models.ThirdPartyDataItem(
                tdid="<TDID>",
                data=[
                    models.ThirdPartyData(name="in_market_auto"),
                ],
            )
        ],
    )
```

### 3. Offline Conversions Data (CAPI)

```python
from ttd_data import DataClient, models

with DataClient() as client:
    response = client.offline_conversion.ingest_offline_conversion_data(
        ttd_auth=TTD_AUTH_TOKEN,
        data_provider_id=DATA_PROVIDER_ID,
        items=[
            models.OfflineConversionDataItem(
                tracking_tag_id=TRACKING_TAG_ID,
                timestamp_utc=datetime.now(timezone.utc),
                tdid="<TDID>",
            )
        ],
    )
```

### 4. Optouts and Deletion - Advertiser - Data Subject Request

```python
from ttd_data import DataClient, models

with DataClient() as client:
    response = client.deletion_opt_out.data_subject_request_advertiser_data(
        ttd_auth=TTD_AUTH_TOKEN,
        advertiser_id=ADVERTISER_ID,
        request_type=models.PartnerDsrRequestType.DELETION,
        items=[
            models.PartnerDsrDataItem(tdid="<TDID>"),
            models.PartnerDsrDataItem(daid="<DAID>"),
            models.PartnerDsrDataItem(euid="<EUID>"),
        ],
    )
```

### 5. Optouts and Deletion - Data Provider - Data Subject Request

```python
from ttd_data import DataClient, models

with DataClient() as client:
    response = client.deletion_opt_out.data_subject_request_third_party_data(
        ttd_auth=TTD_AUTH_TOKEN,
        data_provider_id=DATA_PROVIDER_ID,
        request_type=models.PartnerDsrRequestType.OPT_OUT,
        items=[
            models.PartnerDsrDataItem(tdid="<TDID>"),
            models.PartnerDsrDataItem(ramp_id="<RAMP_ID>"),
        ],
    )
```

### 6. Optouts and Deletion - Merchant - Data Subject Request

```python
from ttd_data import DataClient, models

with DataClient() as client:
    response = client.deletion_opt_out.data_subject_request_merchant_data(
        ttd_auth=TTD_AUTH_TOKEN,
        merchant_id=MERCHANT_ID,
        request_type=models.PartnerDsrRequestType.DELETION,
        items=[
            models.PartnerDsrDataItem(tdid="<TDID>"),
        ],
    )
```


### 7. Async usage

The same SDK client can also be used to make asynchronous requests by importing asyncio.

```python
# Asynchronous Example
import asyncio
from ttd_data import DataClient, models

async def main():

    async with DataClient() as data_client:
        response = client.advertiser.ingest_advertiser_data(
            ttd_auth=TTD_AUTH_TOKEN,
            advertiser_id=ADVERTISER_ID,
            items=[
                models.AdvertiserDataItem(
                    tdid="<TDID>",
                    data=[
                        models.AdvertiserData(name="loyalty_members"),
                    ],
                )
            ],
        )

        # Handle response
        print(response.advertiser_data_server_response)

asyncio.run(main())
```
<!-- No SDK Example Usage [usage] -->

<!-- Start Available Resources and Operations [operations] -->
## Available Resources and Operations

<details open>
<summary>Available methods</summary>

### [Advertiser](docs/sdks/advertiser/README.md)

* [ingest_advertiser_data](docs/sdks/advertiser/README.md#ingest_advertiser_data) - Upload first-party data for the specified ID for use in audience targeting.

### [DeletionOptOut](docs/sdks/deletionoptout/README.md)

* [data_subject_request_advertiser_data](docs/sdks/deletionoptout/README.md#data_subject_request_advertiser_data) - Delete IDs shared with The Trade Desk for the specified advertiser ID.
* [data_subject_request_merchant_data](docs/sdks/deletionoptout/README.md#data_subject_request_merchant_data) - Delete IDs shared with The Trade Desk via a product catalog for the specified merchant ID.
* [data_subject_request_third_party_data](docs/sdks/deletionoptout/README.md#data_subject_request_third_party_data) - Delete IDs shared with The Trade Desk for the specified data provider ID.

### [OfflineConversion](docs/sdks/offlineconversion/README.md)

* [ingest_offline_conversion_data](docs/sdks/offlineconversion/README.md#ingest_offline_conversion_data) - Upload offline conversion data for the specified data provider.

### [ThirdParty](docs/sdks/thirdparty/README.md)

* [ingest_third_party_data](docs/sdks/thirdparty/README.md#ingest_third_party_data) - Upload third-party data for the specified data provider for use in audience targeting.

</details>
<!-- End Available Resources and Operations [operations] -->

<!-- Start Retries [retries] -->
## Retries

Some of the endpoints in this SDK support retries. If you use the SDK without any configuration, it will fall back to the default retry strategy provided by the API. However, the default retry strategy can be overridden on a per-operation basis, or across the entire SDK.

To change the default retry strategy for a single API call, simply provide a `RetryConfig` object to the call:
```python
from ttd_data import BaseDataClient
from ttd_data.utils import BackoffStrategy, RetryConfig


with BaseDataClient() as base_data_client:

    res = base_data_client.advertiser.ingest_advertiser_data(ttd_auth="<value>", advertiser_id="<id>",
        RetryConfig("backoff", BackoffStrategy(1, 50, 1.1, 100), False))

    assert res.advertiser_data_server_response is not None

    # Handle response
    print(res.advertiser_data_server_response)

```

If you'd like to override the default retry strategy for all operations that support retries, you can use the `retry_config` optional parameter when initializing the SDK:
```python
from ttd_data import BaseDataClient
from ttd_data.utils import BackoffStrategy, RetryConfig


with BaseDataClient(
    retry_config=RetryConfig("backoff", BackoffStrategy(1, 50, 1.1, 100), False),
) as base_data_client:

    res = base_data_client.advertiser.ingest_advertiser_data(ttd_auth="<value>", advertiser_id="<id>")

    assert res.advertiser_data_server_response is not None

    # Handle response
    print(res.advertiser_data_server_response)

```
<!-- End Retries [retries] -->

<!-- Start Error Handling [errors] -->
## Error Handling

[`DataError`](./src/ttd_data/errors/dataerror.py) is the base class for all HTTP error responses. It has the following properties:

| Property           | Type             | Description                                                                             |
| ------------------ | ---------------- | --------------------------------------------------------------------------------------- |
| `err.message`      | `str`            | Error message                                                                           |
| `err.status_code`  | `int`            | HTTP response status code eg `404`                                                      |
| `err.headers`      | `httpx.Headers`  | HTTP response headers                                                                   |
| `err.body`         | `str`            | HTTP body. Can be empty string if no body is returned.                                  |
| `err.raw_response` | `httpx.Response` | Raw HTTP response                                                                       |
| `err.data`         |                  | Optional. Some errors may contain structured data. [See Error Classes](#error-classes). |

### Example
```python
from ttd_data import BaseDataClient, errors


with BaseDataClient() as base_data_client:
    res = None
    try:

        res = base_data_client.advertiser.ingest_advertiser_data(ttd_auth="<value>", advertiser_id="<id>")

        assert res.advertiser_data_server_response is not None

        # Handle response
        print(res.advertiser_data_server_response)


    except errors.DataError as e:
        # The base class for HTTP error responses
        print(e.message)
        print(e.status_code)
        print(e.body)
        print(e.headers)
        print(e.raw_response)

        # Depending on the method different errors may be thrown
        if isinstance(e, errors.AdvertiserDataServerResponseError):
            print(e.data.failed_lines)  # OptionalNullable[List[models.AdvertiserDataServerResponseLine]]
            print(e.data.http_meta)  # models.HTTPMetadata
```

### Error Classes
**Primary error:**
* [`DataError`](./src/ttd_data/errors/dataerror.py): The base class for HTTP error responses.

<details><summary>Less common errors (11)</summary>

<br />

**Network errors:**
* [`httpx.RequestError`](https://www.python-httpx.org/exceptions/#httpx.RequestError): Base class for request errors.
    * [`httpx.ConnectError`](https://www.python-httpx.org/exceptions/#httpx.ConnectError): HTTP client was unable to make a request to a server.
    * [`httpx.TimeoutException`](https://www.python-httpx.org/exceptions/#httpx.TimeoutException): HTTP request timed out.


**Inherit from [`DataError`](./src/ttd_data/errors/dataerror.py)**:
* [`AdvertiserDataServerResponseError`](./src/ttd_data/errors/advertiserdataserverresponseerror.py): Success. Applicable to 1 of 6 methods.*
* [`ThirdPartyDataServerResponseError`](./src/ttd_data/errors/thirdpartydataserverresponseerror.py): Success. Applicable to 1 of 6 methods.*
* [`OfflineConversionDataServerResponseError`](./src/ttd_data/errors/offlineconversiondataserverresponseerror.py): Success. Applicable to 1 of 6 methods.*
* [`AdvertiserDsrResponseError`](./src/ttd_data/errors/advertiserdsrresponseerror.py): Success. Applicable to 1 of 6 methods.*
* [`MerchantDsrResponseError`](./src/ttd_data/errors/merchantdsrresponseerror.py): Success. Applicable to 1 of 6 methods.*
* [`ThirdPartyDsrResponseError`](./src/ttd_data/errors/thirdpartydsrresponseerror.py): Success. Applicable to 1 of 6 methods.*
* [`ResponseValidationError`](./src/ttd_data/errors/responsevalidationerror.py): Type mismatch between the response data and the expected Pydantic model. Provides access to the Pydantic validation error via the `cause` attribute.

</details>

\* Check [the method documentation](#available-resources-and-operations) to see if the error is applicable.
<!-- End Error Handling [errors] -->

<!-- Start Custom HTTP Client [http-client] -->
## Custom HTTP Client

The Python SDK makes API calls using the [httpx](https://www.python-httpx.org/) HTTP library.  In order to provide a convenient way to configure timeouts, cookies, proxies, custom headers, and other low-level configuration, you can initialize the SDK client with your own HTTP client instance.
Depending on whether you are using the sync or async version of the SDK, you can pass an instance of `HttpClient` or `AsyncHttpClient` respectively, which are Protocol's ensuring that the client has the necessary methods to make API calls.
This allows you to wrap the client with your own custom logic, such as adding custom headers, logging, or error handling, or you can just pass an instance of `httpx.Client` or `httpx.AsyncClient` directly.

For example, you could specify a header for every request that this sdk makes as follows:
```python
from ttd_data import BaseDataClient
import httpx

http_client = httpx.Client(headers={"x-custom-header": "someValue"})
s = BaseDataClient(client=http_client)
```

or you could wrap the client with your own custom logic:
```python
from ttd_data import BaseDataClient
from ttd_data.httpclient import AsyncHttpClient
import httpx

class CustomClient(AsyncHttpClient):
    client: AsyncHttpClient

    def __init__(self, client: AsyncHttpClient):
        self.client = client

    async def send(
        self,
        request: httpx.Request,
        *,
        stream: bool = False,
        auth: Union[
            httpx._types.AuthTypes, httpx._client.UseClientDefault, None
        ] = httpx.USE_CLIENT_DEFAULT,
        follow_redirects: Union[
            bool, httpx._client.UseClientDefault
        ] = httpx.USE_CLIENT_DEFAULT,
    ) -> httpx.Response:
        request.headers["Client-Level-Header"] = "added by client"

        return await self.client.send(
            request, stream=stream, auth=auth, follow_redirects=follow_redirects
        )

    def build_request(
        self,
        method: str,
        url: httpx._types.URLTypes,
        *,
        content: Optional[httpx._types.RequestContent] = None,
        data: Optional[httpx._types.RequestData] = None,
        files: Optional[httpx._types.RequestFiles] = None,
        json: Optional[Any] = None,
        params: Optional[httpx._types.QueryParamTypes] = None,
        headers: Optional[httpx._types.HeaderTypes] = None,
        cookies: Optional[httpx._types.CookieTypes] = None,
        timeout: Union[
            httpx._types.TimeoutTypes, httpx._client.UseClientDefault
        ] = httpx.USE_CLIENT_DEFAULT,
        extensions: Optional[httpx._types.RequestExtensions] = None,
    ) -> httpx.Request:
        return self.client.build_request(
            method,
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            extensions=extensions,
        )

s = BaseDataClient(async_client=CustomClient(httpx.AsyncClient()))
```
<!-- End Custom HTTP Client [http-client] -->

<!-- Start Resource Management [resource-management] -->
## Resource Management

The `BaseDataClient` class implements the context manager protocol and registers a finalizer function to close the underlying sync and async HTTPX clients it uses under the hood. This will close HTTP connections, release memory and free up other resources held by the SDK. In short-lived Python programs and notebooks that make a few SDK method calls, resource management may not be a concern. However, in longer-lived programs, it is beneficial to create a single SDK instance via a [context manager][context-manager] and reuse it across the application.

[context-manager]: https://docs.python.org/3/reference/datamodel.html#context-managers

```python
from ttd_data import BaseDataClient
def main():

    with BaseDataClient() as base_data_client:
        # Rest of application here...


# Or when using async:
async def amain():

    async with BaseDataClient() as base_data_client:
        # Rest of application here...
```
<!-- End Resource Management [resource-management] -->

<!-- Start Debugging [debug] -->
## Debugging

You can setup your SDK to emit debug logs for SDK requests and responses.

You can pass your own logger class directly into your SDK.
```python
from ttd_data import BaseDataClient
import logging

logging.basicConfig(level=logging.DEBUG)
s = BaseDataClient(server_url="https://example.com", debug_logger=logging.getLogger("ttd_data"))
```

You can also enable a default debug logger by setting an environment variable `TTD_DATA_DEBUG` to true.
<!-- End Debugging [debug] -->

<!-- Placeholder for Future Speakeasy SDK Sections -->

# Development

## Maturity

This SDK is in beta, and there may be breaking changes between versions without a major version update. Therefore, we recommend pinning usage
to a specific package version. This way, you can install the same version each time without breaking changes unless you are intentionally
looking for the latest version.

## Contributions

While we value open-source contributions to this SDK, this library is generated programmatically. Any manual changes added to internal files will be overwritten on the next generation. 
We look forward to hearing your feedback. Feel free to open a PR or an issue with a proof of concept and we'll do our best to include it in a future release. 

### SDK Created by [Speakeasy](https://www.speakeasy.com/?utm_source=ttd-data&utm_campaign=python)
