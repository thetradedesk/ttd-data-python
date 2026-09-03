"""GraphQL request execution against the TTD Platform API supergraph.

Knows nothing about any particular domain: the operation classes hold one of
these and call `execute`.
"""

from typing import Any, Callable, Dict, Final, List, Mapping, Optional, Union

import httpx
from ttd_data import utils
from ttd_data.errors import APIError
from ttd_data.graphql._response import GraphQLError
from ttd_data.httpclient import HttpClient
from ttd_data.sdkconfiguration import SDKConfiguration
from ttd_data.types import OptionalNullable, UNSET
from ttd_data.utils import RetryConfig
from ttd_data.utils.logger import Logger, get_default_logger


AUTH_HEADER: Final = "TTD-Auth"

TtdAuth = Optional[Union[str, Callable[[], Optional[str]]]]

# Same set the generated REST operations retry on.
RETRYABLE_STATUS_CODES: Final[List[str]] = ["429", "500", "502", "503", "504"]


def _redacted(headers: Mapping[str, str]) -> Dict[str, str]:
    """Headers with the credential masked, for logging."""
    return {
        key: ("***" if key.lower() == AUTH_HEADER.lower() else value)
        for key, value in headers.items()
    }


class GraphQLTransport:
    """Sends GraphQL documents and returns the parsed response body. Use it
    directly for any operation the typed operation classes do not cover.
    """

    sdk_configuration: SDKConfiguration

    DEFAULT_ENDPOINT = "https://api.gen.adsrvr.org/graphql"

    def __init__(
        self,
        server_url: Optional[str] = None,
        client: Optional[HttpClient] = None,
        retry_config: OptionalNullable[RetryConfig] = UNSET,
        timeout_ms: Optional[int] = None,
        debug_logger: Optional[Logger] = None,
        ttd_auth: TtdAuth = None,
    ) -> None:
        client_supplied = client is not None
        self.sdk_configuration = SDKConfiguration(
            client=client or httpx.Client(follow_redirects=True),
            client_supplied=client_supplied,
            async_client=None,
            async_client_supplied=False,
            server_url=server_url or self.DEFAULT_ENDPOINT,
            retry_config=retry_config,
            timeout_ms=timeout_ms,
            debug_logger=debug_logger or get_default_logger(),
        )
        self._ttd_auth = ttd_auth

    def _default_ttd_auth(self) -> Optional[str]:
        """Resolve the client-configured credential, calling it if it is
        a rotating-token callable."""
        auth = self._ttd_auth
        return auth() if callable(auth) else auth

    def execute(
        self,
        query: str,
        *,
        ttd_auth: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        retries: OptionalNullable[RetryConfig] = UNSET,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute an arbitrary GraphQL query or mutation.

        POSTs the request and returns the parsed JSON body.

        :param query: Full GraphQL query/mutation document.
        :param ttd_auth: Platform API token. Sent as the `TTD-Auth` header.
            Defaults to the credential this transport was constructed with;
            pass this to use a different token for this call only.
        :param variables: GraphQL variables referenced by the query.
        :param retries: Override the client's retry configuration for this call.
        :raises ValueError: no `ttd_auth` was passed and none is configured
            on the client, or the resolved token is empty.
        :raises GraphQLError: The response carried top-level `errors`. The
            supergraph reports authorization and policy failures this way, with
            HTTP 200, so this is the usual failure path rather than an edge case.
        :raises APIError: Non-2xx response, matching the REST operations.
        """
        resolved_ttd_auth = ttd_auth or self._default_ttd_auth()
        if not resolved_ttd_auth:
            raise ValueError("ttd_auth must be a non-empty platform API token")

        client = self.sdk_configuration.client
        if client is None:
            raise ValueError("client is required")

        headers = {
            "Content-Type": "application/json",
            "apollographql-client-name": "ttd-data-python",
        }
        if http_headers:
            headers.update(http_headers)
        # Last, so the typed credential always wins over a stray header entry.
        headers[AUTH_HEADER] = resolved_ttd_auth

        effective_timeout_ms = timeout_ms or self.sdk_configuration.timeout_ms
        timeout = (
            effective_timeout_ms / 1000
            if effective_timeout_ms is not None
            else httpx.USE_CLIENT_DEFAULT
        )

        url = self.sdk_configuration.server_url or self.DEFAULT_ENDPOINT
        request = client.build_request(
            "POST",
            url,
            json={"query": query, "variables": variables or {}},
            headers=headers,
            timeout=timeout,
        )

        if retries == UNSET and self.sdk_configuration.retry_config is not UNSET:
            retries = self.sdk_configuration.retry_config

        logger = self.sdk_configuration.debug_logger

        def send() -> httpx.Response:
            logger.debug(
                "GraphQL request:\nURL: %s\nHeaders: %s\nBody: %s",
                url,
                _redacted(headers),
                request.content,
            )
            res = client.send(request)
            logger.debug(
                "GraphQL response:\nStatus Code: %s\nBody: %s", res.status_code, res.text
            )
            return res

        if isinstance(retries, RetryConfig):
            response = utils.retry(
                send, utils.Retries(retries, RETRYABLE_STATUS_CODES)
            )
        else:
            response = send()

        if not response.is_success:
            raise APIError("API error occurred", response, response.text)

        body = response.json()
        if body.get("errors"):
            raise GraphQLError(body["errors"], response, body.get("data"))
        return body
