"""Unit tests for GraphQL retries and debug logging: the transport honours the
client's retry configuration, a call can override it, and the credential never
reaches the log."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

import httpx
import pytest

from ttd_data.errors import APIError
from ttd_data.graphql import GraphQLTransport
from ttd_data.utils import BackoffStrategy, RetryConfig

QUERY = "query { __typename }"

# Tight enough that a retrying test costs milliseconds, not seconds.
FAST_BACKOFF = BackoffStrategy(
    initial_interval=1, max_interval=1, exponent=1.0, max_elapsed_time=1000, jitter_ms=0
)


def backoff_config() -> RetryConfig:
    return RetryConfig("backoff", FAST_BACKOFF, retry_connection_errors=False)


class StatusSequence:
    """Replays one status code per attempt, counting attempts."""

    def __init__(self, statuses: Sequence[int]) -> None:
        self._statuses = list(statuses)
        self.attempts = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        status = self._statuses[min(self.attempts, len(self._statuses) - 1)]
        self.attempts += 1
        return httpx.Response(status, json={"data": {"__typename": "Query"}})


class CollectingLogger:
    def __init__(self) -> None:
        self.lines: List[str] = []

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.lines.append(msg % args if args else msg)


def transport(statuses: Sequence[int], **kwargs: Any):
    sequence = StatusSequence(statuses)
    client = httpx.Client(transport=httpx.MockTransport(sequence.handler))
    return GraphQLTransport(client=client, **kwargs), sequence


def test_a_retryable_status_is_retried():
    """One representative status is enough: RETRYABLE_STATUS_CODES is a flat
    membership check, with no per-status branch to exercise separately."""
    gql, sequence = transport([429, 200], retry_config=backoff_config())

    body: Dict[str, Any] = gql.execute(QUERY, ttd_auth="token")

    assert sequence.attempts == 2
    assert body["data"]["__typename"] == "Query"


def test_non_retryable_status_fails_on_the_first_attempt():
    """A 400 is the caller's fault; retrying it just delays the error."""
    gql, sequence = transport([400], retry_config=backoff_config())

    with pytest.raises(APIError):
        gql.execute(QUERY, ttd_auth="token")

    assert sequence.attempts == 1


def test_without_a_retry_config_a_429_is_raised_immediately():
    """Retries stay opt-in, so behaviour is unchanged for callers who set none."""
    gql, sequence = transport([429, 200])

    with pytest.raises(APIError):
        gql.execute(QUERY, ttd_auth="token")

    assert sequence.attempts == 1


def test_per_call_retries_override_the_client_configuration():
    """A client configured not to retry can still retry one call."""
    gql, sequence = transport(
        [429, 200],
        retry_config=RetryConfig(
            "none", FAST_BACKOFF, retry_connection_errors=False
        ),
    )

    gql.execute(QUERY, ttd_auth="token", retries=backoff_config())

    assert sequence.attempts == 2


def test_data_client_retry_config_reaches_graphql():
    """The bug this closes: retry_config set on DataClient used to apply to the
    REST operations only."""
    from ttd_data import DataClient

    config = backoff_config()
    client = DataClient(retry_config=config)

    assert client.graphql.sdk_configuration.retry_config is config


def test_the_credential_is_masked_in_debug_output():
    """Debug logging dumps the request headers; the token must not be among
    them, which is only enforceable because auth is a typed parameter."""
    logger = CollectingLogger()
    gql, _ = transport([200], debug_logger=logger)

    gql.execute(QUERY, ttd_auth="super-secret-token")

    logged = "\n".join(logger.lines)
    assert "super-secret-token" not in logged
    assert "'TTD-Auth': '***'" in logged
