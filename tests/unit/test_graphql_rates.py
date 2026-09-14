"""Unit tests for the data rate GraphQL operations: what document and
variables go on the wire, and how the two independent filters compose."""

from __future__ import annotations

import pytest


@pytest.fixture
def graphql_client(graphql_ops):
    from ttd_data.graphql.rates import DataRateOperations

    def make(response=None):
        return graphql_ops(DataRateOperations, response, ttd_auth="tok")

    return make


def test_query_brands_sends_paging_variables(graphql_client):
    client, recorder = graphql_client()

    client.query_brands(provider_id="eltoro", first=10, after="cursor-1")

    assert recorder.last_variables == {
        "providerId": "eltoro",
        "first": 10,
        "after": "cursor-1",
    }
    assert "QueryThirdPartyDataBrands" in recorder.last_query


def test_query_segment_data_rates_omits_both_filters_when_unset(graphql_client):
    client, recorder = graphql_client()

    client.query_segment_data_rates(provider_id="eltoro")

    variables = recorder.last_variables
    assert variables == {"providerId": "eltoro", "first": 1000, "after": None}
    assert "where" not in variables
    assert "rateWhere" not in variables


def test_query_segment_data_rates_applies_segment_and_brand_filters(graphql_client):
    client, recorder = graphql_client()

    client.query_segment_data_rates(
        provider_id="eltoro",
        provider_element_ids=["seg-1"],
        brand_id="eltororetail",
    )

    variables = recorder.last_variables
    assert variables["where"] == {"providerElementId": {"in": ["seg-1"]}}
    assert variables["rateWhere"] == {"thirdPartyDataBrandId": {"eq": "eltororetail"}}


def test_query_segment_data_rates_brand_filter_is_independent(graphql_client):
    """Filtering by brand alone must not imply a segment filter."""
    client, recorder = graphql_client()

    client.query_segment_data_rates(provider_id="eltoro", brand_id="eltororetail")

    variables = recorder.last_variables
    assert "where" not in variables
    assert variables["rateWhere"] == {"thirdPartyDataBrandId": {"eq": "eltororetail"}}


def test_query_data_rate_batches_lists_all_batches_by_default(graphql_client):
    client, recorder = graphql_client()

    client.query_data_rate_batches(provider_id="eltoro")

    variables = recorder.last_variables
    assert variables == {"providerId": "eltoro", "first": 10, "after": None}
    assert "where" not in variables


def test_query_data_rate_batches_filters_to_one_batch(graphql_client):
    response = {
        "data": {
            "thirdPartyDataProvider": {
                "dataRateBatches": {
                    "totalCount": 1,
                    "nodes": [
                        {
                            "id": "0006A7D",
                            "processingStatus": "SUCCESSFUL",
                            "approvalStatus": "APPROVED",
                        }
                    ],
                }
            }
        }
    }
    client, recorder = graphql_client(response)

    page = client.query_data_rate_batches(provider_id="eltoro", batch_id="0006A7D")

    assert recorder.last_variables["where"] == {"id": {"eq": "0006A7D"}}
    assert page.total_count == 1
    assert page.nodes[0]["processingStatus"] == "SUCCESSFUL"


def cpm_rate(element_id="seg-1", brand_id="brand-1", **overrides):
    rate = {
        "providerElementId": element_id,
        "thirdPartyDataBrandId": brand_id,
        "cost": {"cpm": {"cpmCost": {"amount": 2.5, "currencyCode": "USD"}}},
    }
    rate.update(overrides)
    return rate


def test_create_data_rate_batch_wraps_input_and_defaults_to_api_source(graphql_client):
    client, recorder = graphql_client()

    client.create_data_rate_batch(
        provider_id="eltoro",
        data_rates=[cpm_rate()],
    )

    assert recorder.last_variables == {
        "input": {
            "dataProviderId": "eltoro",
            "dataRates": [{"create": cpm_rate()}],
            "submissionSource": "API",
        }
    }
    assert "DataRateBatchCreate" in recorder.last_query


def test_create_data_rate_batch_wraps_each_rate_under_create(graphql_client):
    client, recorder = graphql_client()

    client.create_data_rate_batch(
        provider_id="eltoro",
        data_rates=[cpm_rate(element_id="seg-1"), cpm_rate(element_id="seg-2")],
        submission_source="PARTNER_PORTAL_UI",
    )

    variables = recorder.last_variables["input"]
    assert variables["dataRates"] == [
        {"create": cpm_rate(element_id="seg-1")},
        {"create": cpm_rate(element_id="seg-2")},
    ]
    assert variables["submissionSource"] == "PARTNER_PORTAL_UI"


def test_create_data_rate_batch_splits_payload_into_data_and_errors(graphql_client):
    response = {
        "data": {
            "dataRateBatchCreate": {
                "data": {
                    "id": "0006A7D",
                    "processingStatus": "NOT_STARTED",
                    "approvalStatus": "AWAITING_MANUAL_REVIEW",
                },
                "errors": None,
            }
        }
    }
    client, _ = graphql_client(response)

    result = client.create_data_rate_batch(
        provider_id="eltoro",
        data_rates=[cpm_rate()],
    )

    assert result.data["id"] == "0006A7D"
    assert result.data["approvalStatus"] == "AWAITING_MANUAL_REVIEW"
    assert result.errors == []


def test_create_data_rate_batch_surfaces_rejection_errors(graphql_client):
    response = {
        "data": {
            "dataRateBatchCreate": {
                "data": None,
                "errors": [
                    {
                        "__typename": "UserError",
                        "message": "At least one data rate object must be provided.",
                        "field": ["dataRates"],
                    }
                ],
            }
        }
    }
    client, _ = graphql_client(response)

    result = client.create_data_rate_batch(
        provider_id="eltoro",
        data_rates=[cpm_rate()],
    )

    assert result.data is None
    assert result.errors[0]["field"] == ["dataRates"]


@pytest.mark.parametrize("size", [0, 5001])
def test_create_data_rate_batch_rejects_batch_outside_limits(graphql_client, size):
    client, recorder = graphql_client()

    with pytest.raises(ValueError, match="between 1 and 5000"):
        client.create_data_rate_batch(
            provider_id="eltoro",
            data_rates=[cpm_rate()] * size,
        )

    assert recorder.requests == []


@pytest.mark.parametrize(
    "rate, expected",
    [
        (
            {"providerElementId": "seg-1", "thirdPartyDataBrandId": "brand-1"},
            r"data_rates\[0\]\.cost is required",
        ),
        (
            cpm_rate(
                cost={
                    "cpm": {"cpmCost": {"amount": 2.5, "currencyCode": "USD"}},
                    "revShare": {"percentOfMediaCost": 0.12},
                }
            ),
            r"data_rates\[0\]\.cost must set exactly one",
        ),
        (
            cpm_rate(
                subject={
                    "partner": {"partnerId": "p-1"},
                    "advertiser": {"advertiserId": "a-1"},
                }
            ),
            r"data_rates\[0\]\.subject must set exactly one",
        ),
    ],
)
def test_create_data_rate_batch_enforces_one_of_inputs(graphql_client, rate, expected):
    """@oneOf violations are caught before a request goes out, since the server
    rejects the whole batch for one malformed entry."""
    client, recorder = graphql_client()

    with pytest.raises(ValueError, match=expected):
        client.create_data_rate_batch(
            provider_id="eltoro",
            data_rates=[rate],
        )

    assert recorder.requests == []
