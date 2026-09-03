"""Unit tests for GraphQL authentication: the empty-token guard, and the
typed credential taking precedence over a caller-supplied header."""

from __future__ import annotations

import pytest


@pytest.fixture
def graphql_client(graphql_ops):
    from ttd_data.graphql import TaxonomyOperations

    def make(response=None, ttd_auth=None):
        return graphql_ops(TaxonomyOperations, response, ttd_auth=ttd_auth)

    return make


def test_empty_token_is_rejected(graphql_client):
    """`ttd_auth: str` cannot catch an empty string, so the transport does —
    before spending a request on a guaranteed 401."""
    client, recorder = graphql_client()

    with pytest.raises(ValueError, match="non-empty"):
        client.query_segments(ttd_auth="", provider_id="eltoro")

    assert recorder.requests == []


def test_token_argument_wins_over_a_stray_header(graphql_client):
    """The credential is applied after the caller's headers are merged, so a
    caller who also puts TTD-Auth in http_headers cannot silently override it.
    Also pins the header name the token is sent under."""
    client, recorder = graphql_client()

    client.query_segments(
        ttd_auth="the-real-token",
        provider_id="eltoro",
        http_headers={"TTD-Auth": "stale-token"},
    )

    assert recorder.requests[-1]["headers"]["ttd-auth"] == "the-real-token"


def test_falls_back_to_the_client_configured_token(graphql_client):
    """A call with no `ttd_auth` uses the credential the transport was built
    with, so a `DataClient(ttd_auth=...)` needs no per-call token."""
    client, recorder = graphql_client(ttd_auth="client-token")

    client.query_segments(provider_id="eltoro")

    assert recorder.requests[-1]["headers"]["ttd-auth"] == "client-token"


def test_per_call_token_overrides_the_client_configured_token(graphql_client):
    """An explicit `ttd_auth` still wins over the client-configured one, so a
    single client can serve several tokens when needed."""
    client, recorder = graphql_client(ttd_auth="client-token")

    client.query_segments(ttd_auth="call-token", provider_id="eltoro")

    assert recorder.requests[-1]["headers"]["ttd-auth"] == "call-token"
