"""Third-party data rate operations: brands, per-segment data rates, and data
rate batch submission and lookup.
"""

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from typing_extensions import NotRequired, TypedDict

from ttd_data.graphql._response import (
    MutationResult,
    Page,
    build_mutation_result,
    build_page,
)
from ttd_data.graphql._transport import GraphQLTransport
from ttd_data.types import OptionalNullable, UNSET
from ttd_data.utils import RetryConfig

BRANDS_PATH = ("thirdPartyDataProvider", "thirdPartyDataBrands")
SEGMENTS_PATH = ("thirdPartyDataProvider", "thirdPartyTargetingDataSegments")
BATCHES_PATH = ("thirdPartyDataProvider", "dataRateBatches")
BATCH_CREATE_PATH = ("dataRateBatchCreate",)

MAX_BATCH_SIZE = 5000


class DataRateInput(TypedDict):
    """A `DataRateCreateInput`. Creates the rate, or overwrites the existing
    rate for the same segment, brand and subject.

    `subject` (a `DataRateSubjectCreateInput`) sets exactly one of `partner`
    (`{"partnerId": ...}`) or `advertiser` (`{"advertiserId": ...}`) — omit it
    entirely for a system (syndicated) rate. `cost` (a
    `DataRateCostCreateInput`) sets exactly one of:
      - `cpm`: `{"cpmCost": {"amount": ..., "currencyCode": ...}}`
      - `revShare`: `{"percentOfMediaCost": ...}` — a fraction, not a
        percentage: 0.12 means 12%.
      - `hybrid`: `{"cpmCostCap": {"amount": ..., "currencyCode": ...},
        "percentOfMediaCost": ...}`

    The schema's `DataRateInput.delete` variant (removing an existing rate)
    isn't supported yet.
    """

    providerElementId: str
    thirdPartyDataBrandId: str
    cost: Dict[str, Any]
    subject: NotRequired[Dict[str, Any]]


def _require_exactly_one(
    value: Mapping[str, Any], keys: Sequence[str], label: str
) -> str:
    """Enforce a `@oneOf` input, which the server rejects outright otherwise."""
    unknown = sorted(set(value) - set(keys))
    if unknown:
        raise ValueError(f"{label} has unknown key(s) {unknown}; allowed: {list(keys)}")
    present = [key for key in keys if value.get(key) is not None]
    if len(present) != 1:
        raise ValueError(
            f"{label} must set exactly one of {list(keys)}, got {present or 'none'}"
        )
    return present[0]


def _validate_rate(rate: Mapping[str, Any], index: int) -> None:
    label = f"data_rates[{index}]"

    subject = rate.get("subject")
    if subject is not None:
        _require_exactly_one(subject, ("partner", "advertiser"), f"{label}.subject")

    cost = rate.get("cost")
    if cost is None:
        raise ValueError(f"{label}.cost is required")
    _require_exactly_one(cost, ("cpm", "revShare", "hybrid"), f"{label}.cost")

QUERY_BRANDS = """
query QueryThirdPartyDataBrands($providerId: ID!, $first: Int, $after: String) {
  thirdPartyDataProvider(id: $providerId) {
    thirdPartyDataBrands(first: $first, after: $after) {
      totalCount
      nodes {
        id
        name
        brandDomainName
        logoUrl
        hasRestrictions
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""

QUERY_SEGMENT_DATA_RATES = """
query QuerySegmentDataRates(
  $providerId: ID!
  $first: Int
  $after: String
  $where: ThirdPartyTargetingDataFilterInput
  $rateWhere: ProviderDataRateFilterInput
) {
  thirdPartyDataProvider(id: $providerId) {
    thirdPartyTargetingDataSegments(first: $first, after: $after, where: $where) {
      totalCount
      nodes {
        id
        providerElementId
        providerDataRates(where: $rateWhere) {
          totalCount
          nodes {
            brand {
              id
              name
            }
            dataRateCost {
              __typename
              rateType
              ... on CpmDataRateCost {
                cpmCost {
                  amount
                  currencyCode
                }
              }
              ... on RevShareDataRateCost {
                percentOfMediaCost
              }
              ... on HybridDataRateCost {
                percentOfMediaCost
                cpmCostCap {
                  amount
                  currencyCode
                }
              }
            }
            dataRateSubject {
              __typename
              level
              ... on PartnerDataRateSubject {
                partner {
                  id
                }
              }
              ... on AdvertiserDataRateSubject {
                advertiser {
                  id
                }
              }
            }
            dataRateBatch {
              id
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""

QUERY_DATA_RATE_BATCHES = """
query QueryDataRateBatches(
  $providerId: ID!
  $first: Int
  $after: String
  $where: DataRateBatchFilterInput
) {
  thirdPartyDataProvider(id: $providerId) {
    dataRateBatches(first: $first, after: $after, where: $where) {
      totalCount
      nodes {
        id
        processingStatus
        approvalStatus
        createdAt
        createdBy
        reviewedAt
        earliestEligibleForProcessingTime
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""

CREATE_DATA_RATE_BATCH = """
mutation DataRateBatchCreate($input: DataRateBatchCreateInput!) {
  dataRateBatchCreate(input: $input) {
    data {
      id
      processingStatus
      approvalStatus
      createdAt
      createdBy
      reviewedAt
      earliestEligibleForProcessingTime
    }
    errors {
      __typename
      ... on UserError {
        message
        field
      }
      ... on FieldIsEmptyError {
        message
        field
      }
      ... on StringTooLongError {
        message
        field
        maxLength
      }
    }
  }
}
"""

QUERY_DOCUMENTS: Dict[str, str] = {
    "create_data_rate_batch": CREATE_DATA_RATE_BATCH,
    "query_brands": QUERY_BRANDS,
    "query_segment_data_rates": QUERY_SEGMENT_DATA_RATES,
    "query_data_rate_batches": QUERY_DATA_RATE_BATCHES,
}


class DataRateOperations:
    """Each method sends a fixed document with a fixed field selection;
    arguments become GraphQL variables.
    """

    def __init__(self, transport: GraphQLTransport) -> None:
        self._transport = transport

    def create_data_rate_batch(
        self,
        *,
        provider_id: str,
        data_rates: List[DataRateInput],
        submission_source: str = "API",
        retries: OptionalNullable[RetryConfig] = UNSET,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> MutationResult:
        """
        Submit a batch of data rate creates for one provider.

        The batch is queued rather than applied: the returned
        `processingStatus` starts at NOT_STARTED, and a batch that trips the
        pre-approval thresholds sits at AWAITING_MANUAL_REVIEW until the Data
        Partnerships team approves it. Poll `query_data_rate_batches` with the
        returned batch ID to follow it.

        `errors` being non-empty means the batch was rejected — check it rather
        than assuming a returned result landed.

        The submitter recorded on the batch comes from the email on the
        authenticating token, not from an argument.

        Requires the `ImpalaDataRateBatch` feature flag and the
        `PublicAPI_ThirdPartyData_Edit` permission on the token.

        :param provider_id: ThirdPartyDataProvider ID owning every segment in
            the batch.
        :param data_rates: Rates to create. Where several batches touch one
            segment, the latest submission wins.
        :param submission_source: How the batch was created. Leave as API
            unless you are attributing the batch to a specific tool.
        :raises ValueError: A rate entry does not match the schema's `@oneOf`
            inputs, or the batch is empty or over the limit.
        """
        if not 1 <= len(data_rates) <= MAX_BATCH_SIZE:
            raise ValueError(
                f"data_rates must contain between 1 and {MAX_BATCH_SIZE} "
                f"entries, got {len(data_rates)}"
            )
        for index, rate in enumerate(data_rates):
            _validate_rate(rate, index)

        return build_mutation_result(
            self._transport.execute(
                CREATE_DATA_RATE_BATCH,
                variables={
                    "input": {
                        "dataProviderId": provider_id,
                        "dataRates": [{"create": rate} for rate in data_rates],
                        "submissionSource": submission_source,
                    }
                },
                retries=retries,
                timeout_ms=timeout_ms,
                http_headers=http_headers,
            ),
            *BATCH_CREATE_PATH,
        )

    def query_brands(
        self,
        *,
        provider_id: str,
        first: int = 1000,
        after: Optional[str] = None,
        retries: OptionalNullable[RetryConfig] = UNSET,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> Page:
        """
        Query the third-party data brands belonging to a provider.

        :param provider_id: ThirdPartyDataProvider ID.
        :param first: Page size, capped at 1000 by the schema.
        :param after: Cursor to resume from (pass a previous `Page.end_cursor`).
        """
        return build_page(
            self._transport.execute(
                QUERY_BRANDS,
                variables={"providerId": provider_id, "first": first, "after": after},
                retries=retries,
                timeout_ms=timeout_ms,
                http_headers=http_headers,
            ),
            *BRANDS_PATH,
        )

    def query_segment_data_rates(
        self,
        *,
        provider_id: str,
        provider_element_ids: Optional[Iterable[str]] = None,
        brand_id: Optional[str] = None,
        first: int = 1000,
        after: Optional[str] = None,
        retries: OptionalNullable[RetryConfig] = UNSET,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> Page:
        """
        Query the data rates attached to a provider's segments. Each rate
        carries its brand, cost (CPM, rev-share or hybrid), and the subject the
        rate applies to — `dataRateSubject.level` is SYSTEM, PARTNER or
        ADVERTISER, with the partner or advertiser ID alongside it.

        The schema offers no server-side filter by level, partner or
        advertiser; filter `dataRateSubject` client-side if you need that.

        :param provider_id: ThirdPartyDataProvider ID.
        :param provider_element_ids: Restrict to these provider element IDs.
            Omit to cover every segment for the provider.
        :param brand_id: Restrict the rates to a single brand.
        :param first: Segment page size, capped at 1000 by the schema.
        :param after: Cursor to resume from (pass a previous `Page.end_cursor`).

        Each node is a segment; its rates stay nested under
        `providerDataRates`, which is its own connection.
        """
        variables: Dict[str, Any] = {
            "providerId": provider_id,
            "first": first,
            "after": after,
        }
        if provider_element_ids is not None:
            variables["where"] = {
                "providerElementId": {"in": list(provider_element_ids)}
            }
        if brand_id is not None:
            variables["rateWhere"] = {"thirdPartyDataBrandId": {"eq": brand_id}}
        return build_page(
            self._transport.execute(
                QUERY_SEGMENT_DATA_RATES,
                variables=variables,
                retries=retries,
                timeout_ms=timeout_ms,
                http_headers=http_headers,
            ),
            *SEGMENTS_PATH,
        )

    def query_data_rate_batches(
        self,
        *,
        provider_id: str,
        batch_id: Optional[str] = None,
        first: int = 10,
        after: Optional[str] = None,
        retries: OptionalNullable[RetryConfig] = UNSET,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> Page:
        """
        Query data rate batches for a provider, optionally filtered to one
        batch. Returns batch state only — the schema exposes no edge from a
        batch to the rates it contains.

        :param provider_id: ThirdPartyDataProvider ID.
        :param batch_id: Filter to the batch with this ID. Omit to list all
            batches for the provider.
        :param first: Page size, capped at 1000 by the schema.
        :param after: Cursor to resume from (pass a previous `Page.end_cursor`).
        """
        variables: Dict[str, Any] = {
            "providerId": provider_id,
            "first": first,
            "after": after,
        }
        if batch_id is not None:
            variables["where"] = {"id": {"eq": batch_id}}
        return build_page(
            self._transport.execute(
                QUERY_DATA_RATE_BATCHES,
                variables=variables,
                retries=retries,
                timeout_ms=timeout_ms,
                http_headers=http_headers,
            ),
            *BATCHES_PATH,
        )
