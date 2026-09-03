"""Unit tests for the taxonomy GraphQL operations: what document and variables
go on the wire, and the client-side batch-size guard."""

from __future__ import annotations

import pytest


@pytest.fixture
def graphql_client(graphql_ops):
    from ttd_data.graphql import TaxonomyOperations

    def make(response=None):
        return graphql_ops(TaxonomyOperations, response)

    return make


def test_upsert_segments_sends_the_batch_verbatim(graphql_client):
    """Segments reach the server as given — omitted keys stay omitted, so an
    update touches only the fields the caller passed."""
    client, recorder = graphql_client()
    batch = [
        {
            "providerId": "eltoro",
            "providerElementId": "seg-1",
            "displayName": "Interest > Tech",
            "parentElementId": "ROOT",
            "buyable": False,
        },
        {"providerId": "eltoro", "providerElementId": "seg-2"},
    ]

    client.upsert_segments(ttd_auth="tok", segments=batch)

    assert recorder.last_variables["input"] == batch
    assert "mutation ThirdPartyDataUpsert" in recorder.last_query


@pytest.mark.parametrize("size", [0, 1001])
def test_upsert_segments_rejects_out_of_range_batches(graphql_client, size):
    client, recorder = graphql_client()

    with pytest.raises(ValueError, match="between 1 and 1000"):
        client.upsert_segments(ttd_auth="tok", segments=[{"providerId": "p"}] * size)

    assert recorder.requests == [], "no request should be sent"


def test_query_segments_omits_where_when_unfiltered(graphql_client):
    client, recorder = graphql_client()

    client.query_segments(ttd_auth="tok", provider_id="eltoro")

    variables = recorder.last_variables
    assert variables == {"providerId": "eltoro", "first": 1000, "after": None}
    assert "where" not in variables


def test_query_segments_filters_by_provider_element_ids(graphql_client):
    client, recorder = graphql_client()

    client.query_segments(
        ttd_auth="tok",
        provider_id="eltoro",
        provider_element_ids=("seg-1", "seg-2"),
        first=50,
        after="cursor-abc",
    )

    variables = recorder.last_variables
    assert variables["where"] == {"providerElementId": {"in": ["seg-1", "seg-2"]}}
    assert variables["first"] == 50
    assert variables["after"] == "cursor-abc"


def test_query_segment_taxonomy_status_filters_to_one_segment(graphql_client):
    response = {
        "data": {
            "thirdPartyDataProvider": {
                "thirdPartyTargetingDataSegments": {
                    "nodes": [
                        {"providerElementId": "seg-1", "taxonomyApprovalStatus": "APPROVED"}
                    ]
                }
            }
        }
    }
    client, recorder = graphql_client(response)

    status = client.query_segment_taxonomy_status(
        ttd_auth="tok", provider_id="eltoro", provider_element_id="seg-1"
    )

    assert recorder.last_variables["where"] == {"providerElementId": {"eq": "seg-1"}}
    assert status == "APPROVED"


def test_query_segment_taxonomy_status_returns_none_for_unknown_segment(graphql_client):
    response = {"data": {"thirdPartyDataProvider": {"thirdPartyTargetingDataSegments": {"nodes": []}}}}
    client, _ = graphql_client(response)

    assert (
        client.query_segment_taxonomy_status(
            ttd_auth="tok", provider_id="eltoro", provider_element_id="nope"
        )
        is None
    )
