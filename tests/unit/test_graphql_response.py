"""Unit tests for the GraphQL response envelope: error surfacing, connection
unwrapping, and the per-segment outcome of an upsert."""

from __future__ import annotations

import pytest


@pytest.fixture
def graphql_client(graphql_ops):
    from ttd_data.graphql import TaxonomyOperations

    def make(response=None):
        return graphql_ops(TaxonomyOperations, response)

    return make


def test_graphql_errors_raise_even_on_http_200(graphql_client):
    """The supergraph reports authorization failures as HTTP 200 + errors, so
    returning them as data would let a caller mistake failure for success."""
    from ttd_data.graphql import GraphQLError

    response = {
        "data": None,
        "errors": [{"message": "The current user is not authorized."}],
    }
    client, _ = graphql_client(response)

    with pytest.raises(GraphQLError, match="not authorized"):
        client.query_segments(ttd_auth="tok", provider_id="eltoro")


def test_graphql_failures_are_catchable_as_sdk_errors(graphql_client):
    """One `except DataError` must cover both suites. Before this, GraphQL
    raised bare Exceptions and leaked httpx.HTTPStatusError, so a caller had to
    know the transport library to handle a failure."""
    from ttd_data.errors import DataError

    client, _ = graphql_client({"errors": [{"message": "nope"}]})

    with pytest.raises(DataError) as excinfo:
        client.query_segments(ttd_auth="tok", provider_id="eltoro")

    assert excinfo.value.status_code == 200, "policy failures arrive as HTTP 200"
    assert excinfo.value.raw_response is not None


def test_graphql_error_keeps_partially_resolved_data(graphql_client):
    """GraphQL can return both; the caller must still be able to reach `data`."""
    from ttd_data.graphql import GraphQLError

    response = {
        "data": {"thirdPartyDataProvider": None},
        "errors": [{"message": "policy denied"}],
    }
    client, _ = graphql_client(response)

    with pytest.raises(GraphQLError) as excinfo:
        client.query_segments(ttd_auth="tok", provider_id="eltoro")

    assert excinfo.value.data == {"thirdPartyDataProvider": None}
    assert excinfo.value.errors[0]["message"] == "policy denied"


def test_page_flattens_the_connection(graphql_client):
    response = {
        "data": {
            "thirdPartyDataProvider": {
                "thirdPartyTargetingDataSegments": {
                    "totalCount": 42,
                    "nodes": [{"providerElementId": "seg-1"}],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-abc"},
                }
            }
        }
    }
    client, _ = graphql_client(response)

    page = client.query_segments(ttd_auth="tok", provider_id="eltoro")

    assert page.nodes == [{"providerElementId": "seg-1"}]
    assert page.total_count == 42
    assert page.has_next_page is True
    assert page.end_cursor == "cursor-abc"
    assert page.raw == response, "the untouched body stays reachable"


def test_page_is_empty_when_the_body_does_not_match_the_document(graphql_client):
    """A connection path that does not resolve — a stale path constant, a
    truncated payload — must degrade to an empty page rather than raise from
    deep in a `.get` chain."""
    client, _ = graphql_client({"data": {"thirdPartyDataProvider": None}})

    page = client.query_segments(ttd_auth="tok", provider_id="eltoro")

    assert page.nodes == []
    assert page.total_count is None
    assert page.has_next_page is False


def test_upsert_result_separates_accepted_from_rejected(graphql_client):
    """A partially-applied batch is the dangerous case: the request succeeds
    while some segments are rejected."""
    response = {
        "data": {
            "thirdPartyDataUpsert": {
                "data": [{"mode": "CREATE", "segment": {"providerElementId": "seg-1"}}],
                "errors": [
                    {
                        "__typename": "ThirdPartyDataUpsertOperationError",
                        "providerElementId": "seg-2",
                        "reason": "PARENT_NOT_FOUND",
                    }
                ],
            }
        }
    }
    client, _ = graphql_client(response)

    result = client.upsert_segments(
        ttd_auth="tok",
        segments=[
            {"providerId": "eltoro", "providerElementId": f"seg-{i}"} for i in (1, 2)
        ],
    )

    assert len(result.succeeded) == 1
    assert result.succeeded[0]["mode"] == "CREATE"
    assert len(result.failed) == 1
    assert result.failed[0]["reason"] == "PARENT_NOT_FOUND"


def test_upsert_result_tolerates_omitted_lists(graphql_client):
    """The server may omit `data`/`errors` rather than send them empty; both
    must still read as empty lists, not None."""
    client, _ = graphql_client({"data": {"thirdPartyDataUpsert": {}}})

    result = client.upsert_segments(
        ttd_auth="tok",
        segments=[{"providerId": "eltoro", "providerElementId": "seg-1"}],
    )

    assert result.succeeded == []
    assert result.failed == []
