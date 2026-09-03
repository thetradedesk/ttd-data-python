"""Unit tests for GraphQL authentication: the empty-token guard, and the
client-configured credential taking precedence over a caller-supplied header.
There is no per-call `ttd_auth` — every call authenticates with whatever the
transport was constructed with."""

from __future__ import annotations

import pytest


@pytest.fixture
def graphql_client(graphql_ops):
    from ttd_data.graphql import TaxonomyOperations

    def make(response=None, ttd_auth=None):
        return graphql_ops(TaxonomyOperations, response, ttd_auth=ttd_auth)

    return make


def test_missing_token_is_rejected(graphql_client):
    """No `ttd_auth` configured on the client raises before spending a
    request on a guaranteed 401."""
    client, recorder = graphql_client()

    with pytest.raises(ValueError, match="non-empty"):
        client.query_segments(provider_id="eltoro")

    assert recorder.requests == []


def test_empty_token_is_rejected(graphql_client):
    """An empty string configured on the client is treated the same as no
    token at all."""
    client, recorder = graphql_client(ttd_auth="")

    with pytest.raises(ValueError, match="non-empty"):
        client.query_segments(provider_id="eltoro")

    assert recorder.requests == []


def test_client_token_wins_over_a_stray_header(graphql_client):
    """The credential is applied after the caller's headers are merged, so a
    caller who also puts TTD-Auth in http_headers cannot silently override it.
    Also pins the header name the token is sent under."""
    client, recorder = graphql_client(ttd_auth="the-real-token")

    client.query_segments(
        provider_id="eltoro",
        http_headers={"TTD-Auth": "stale-token"},
    )

    assert recorder.requests[-1]["headers"]["ttd-auth"] == "the-real-token"
