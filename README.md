# ttd-data

Developer-friendly & type-safe Python SDK specifically catered to leverage *ttd-data* API.

[![Built by Speakeasy](https://img.shields.io/badge/Built_by-SPEAKEASY-374151?style=for-the-badge&labelColor=f3f4f6)](https://www.speakeasy.com/?utm_source=ttd-data&utm_campaign=python)
[![License: MIT](https://img.shields.io/badge/LICENSE_//_MIT-3b5bdb?style=for-the-badge&labelColor=eff6ff)](https://mit-license.org/)


<br /><br />
> [!IMPORTANT]
> This SDK is not yet ready for production use. To complete setup please follow the steps outlined in your [workspace](https://app.speakeasy.com/org/thetradedesk/data-api). Delete this section before > publishing to a package manager.

<!-- Start Summary [summary] -->
## Summary


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

from ttd_data import DataClient

sdk = DataClient(
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

<!-- Start SDK Example Usage [usage] -->
## SDK Example Usage

### Example

```python
# Synchronous Example
from ttd_data import DataClient


with DataClient() as data_client:

    res = data_client.advertiser.ingest_advertiser_data(ttd_auth="<value>", advertiser_id="<id>")

    assert res.advertiser_data_server_response is not None

    # Handle response
    print(res.advertiser_data_server_response)
```

</br>

The same SDK client can also be used to make asynchronous requests by importing asyncio.

```python
# Asynchronous Example
import asyncio
from ttd_data import DataClient

async def main():

    async with DataClient() as data_client:

        res = await data_client.advertiser.ingest_advertiser_data_async(ttd_auth="<value>", advertiser_id="<id>")

        assert res.advertiser_data_server_response is not None

        # Handle response
        print(res.advertiser_data_server_response)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->

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
from ttd_data import DataClient
from ttd_data.utils import BackoffStrategy, RetryConfig


with DataClient() as data_client:

    res = data_client.advertiser.ingest_advertiser_data(ttd_auth="<value>", advertiser_id="<id>",
        RetryConfig("backoff", BackoffStrategy(1, 50, 1.1, 100), False))

    assert res.advertiser_data_server_response is not None

    # Handle response
    print(res.advertiser_data_server_response)

```

If you'd like to override the default retry strategy for all operations that support retries, you can use the `retry_config` optional parameter when initializing the SDK:
```python
from ttd_data import DataClient
from ttd_data.utils import BackoffStrategy, RetryConfig


with DataClient(
    retry_config=RetryConfig("backoff", BackoffStrategy(1, 50, 1.1, 100), False),
) as data_client:

    res = data_client.advertiser.ingest_advertiser_data(ttd_auth="<value>", advertiser_id="<id>")

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
from ttd_data import DataClient, errors


with DataClient() as data_client:
    res = None
    try:

        res = data_client.advertiser.ingest_advertiser_data(ttd_auth="<value>", advertiser_id="<id>")

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
from ttd_data import DataClient
import httpx

http_client = httpx.Client(headers={"x-custom-header": "someValue"})
s = DataClient(client=http_client)
```

or you could wrap the client with your own custom logic:
```python
from ttd_data import DataClient
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

s = DataClient(async_client=CustomClient(httpx.AsyncClient()))
```
<!-- End Custom HTTP Client [http-client] -->

<!-- Start Resource Management [resource-management] -->
## Resource Management

The `DataClient` class implements the context manager protocol and registers a finalizer function to close the underlying sync and async HTTPX clients it uses under the hood. This will close HTTP connections, release memory and free up other resources held by the SDK. In short-lived Python programs and notebooks that make a few SDK method calls, resource management may not be a concern. However, in longer-lived programs, it is beneficial to create a single SDK instance via a [context manager][context-manager] and reuse it across the application.

[context-manager]: https://docs.python.org/3/reference/datamodel.html#context-managers

```python
from ttd_data import DataClient
def main():

    with DataClient() as data_client:
        # Rest of application here...


# Or when using async:
async def amain():

    async with DataClient() as data_client:
        # Rest of application here...
```
<!-- End Resource Management [resource-management] -->

<!-- Start Debugging [debug] -->
## Debugging

You can setup your SDK to emit debug logs for SDK requests and responses.

You can pass your own logger class directly into your SDK.
```python
from ttd_data import DataClient
import logging

logging.basicConfig(level=logging.DEBUG)
s = DataClient(server_url="https://example.com", debug_logger=logging.getLogger("ttd_data"))
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
