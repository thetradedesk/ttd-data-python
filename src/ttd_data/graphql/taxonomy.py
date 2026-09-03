"""Third-party data taxonomy operations: segment upsert, segment query, and
taxonomy approval status.
"""

from typing import Any, Dict, Iterable, List, Mapping, Optional

from typing_extensions import NotRequired, TypedDict

from ttd_data.graphql._response import (
    Page,
    UpsertResult,
    build_page,
    build_upsert_result,
)
from ttd_data.graphql._transport import GraphQLTransport
from ttd_data.types import OptionalNullable, UNSET
from ttd_data.utils import RetryConfig

SEGMENTS_PATH = ("thirdPartyDataProvider", "thirdPartyTargetingDataSegments")
UPSERT_PATH = ("thirdPartyDataUpsert",)

MAX_UPSERT_BATCH_SIZE = 1000


class SegmentInput(TypedDict):
    """A `ThirdPartyDataUpsertInput`. Keys are camelCase to match the schema, so
    a segment goes to the server untouched.

    `displayName`, `parentElementId` and `buyable` are additionally required
    when the segment is being created. `isDirectIPTargeting` is honoured on
    create only; `parentElementId` and `subProviderId` are immutable once the
    segment exists.
    """

    providerId: str
    providerElementId: str
    displayName: NotRequired[str]
    parentElementId: NotRequired[str]
    buyable: NotRequired[bool]
    description: NotRequired[str]
    isDirectIPTargeting: NotRequired[bool]
    subProviderId: NotRequired[str]

UPSERT_SEGMENTS = """
mutation ThirdPartyDataUpsert($input: [ThirdPartyDataUpsertInput!]!) {
  thirdPartyDataUpsert(input: $input) {
    data {
      mode
      segment {
        id
        thirdPartyDataId
        providerElementId
        displayName
        description
        fullPath
        buyable
        taxonomyApprovalStatus
        provider {
          id
        }
        parent {
          providerElementId
        }
        subProvider {
          id
        }
        targetingDataInsights {
          lastUpdatedAtUTC
          activeCounts {
            devices
            households
            persons
          }
          receivedCounts {
            totalUserIdCount
          }
        }
      }
    }
    errors {
      __typename
      ... on ThirdPartyDataUpsertOperationError {
        mode
        providerId
        providerElementId
        reason
        message
        field
      }
      ... on ThirdPartyDataUpsertBatchSizeError {
        providedBatchSize
        message
        field
      }
    }
  }
}
"""

QUERY_SEGMENTS = """
query QueryThirdPartyDataSegments(
  $providerId: ID!
  $first: Int
  $after: String
  $where: ThirdPartyTargetingDataFilterInput
) {
  thirdPartyDataProvider(id: $providerId) {
    thirdPartyTargetingDataSegments(first: $first, after: $after, where: $where) {
      totalCount
      nodes {
        id
        thirdPartyDataId
        providerElementId
        displayName
        description
        fullPath
        buyable
        taxonomyApprovalStatus
        createdAt
        subProvider {
          id
        }
        parent {
          providerElementId
        }
        targetingDataInsights {
          lastUpdatedAtUTC
          activeCounts {
            devices
            households
            persons
          }
          receivedCounts {
            totalUserIdCount
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

QUERY_TAXONOMY_STATUS = """
query QueryThirdPartyDataTaxonomyStatus(
  $providerId: ID!
  $where: ThirdPartyTargetingDataFilterInput
) {
  thirdPartyDataProvider(id: $providerId) {
    thirdPartyTargetingDataSegments(first: 1, where: $where) {
      nodes {
        providerElementId
        taxonomyApprovalStatus
      }
    }
  }
}
"""

QUERY_DOCUMENTS: Dict[str, str] = {
    "upsert_segments": UPSERT_SEGMENTS,
    "query_segments": QUERY_SEGMENTS,
    "query_segment_taxonomy_status": QUERY_TAXONOMY_STATUS,
}


class TaxonomyOperations:
    """Each method sends a fixed document with a fixed field selection;
    arguments become GraphQL variables.
    """

    def __init__(self, transport: GraphQLTransport) -> None:
        self._transport = transport

    def upsert_segments(
        self,
        *,
        ttd_auth: Optional[str] = None,
        segments: List[SegmentInput],
        retries: OptionalNullable[RetryConfig] = UNSET,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> UpsertResult:
        """
        Create or update third-party data segments. The server decides per
        segment whether the operation is a CREATE or an UPDATE, reported as
        `mode` on each accepted entry.

        Partially succeeds, so a returned result is not proof the whole batch
        landed — check `failed`.

        :param ttd_auth: Platform API token. Defaults to the client's
            configured credential; pass to use a different token for this
            call only.
        :param segments: Segments to create or update; omit a key to leave that
            field unchanged. Pass a one-element list to upsert a single segment.
        """
        if not 1 <= len(segments) <= MAX_UPSERT_BATCH_SIZE:
            raise ValueError(
                f"segments must contain between 1 and {MAX_UPSERT_BATCH_SIZE} "
                f"entries, got {len(segments)}"
            )
        return build_upsert_result(
            self._transport.execute(
                UPSERT_SEGMENTS,
                ttd_auth=ttd_auth,
                variables={"input": segments},
                retries=retries,
                timeout_ms=timeout_ms,
                http_headers=http_headers,
            ),
            *UPSERT_PATH,
        )

    def query_segments(
        self,
        *,
        ttd_auth: Optional[str] = None,
        provider_id: str,
        provider_element_ids: Optional[Iterable[str]] = None,
        first: int = 1000,
        after: Optional[str] = None,
        retries: OptionalNullable[RetryConfig] = UNSET,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> Page:
        """
        Query a provider's third-party data segments.

        :param ttd_auth: Platform API token. Defaults to the client's
            configured credential; pass to use a different token for this
            call only.
        :param provider_id: ThirdPartyDataProvider ID.
        :param provider_element_ids: Restrict to these provider element IDs.
            Omit to return every segment for the provider.
        :param first: Page size, capped at 1000 by the schema.
        :param after: Cursor to resume from (pass a previous `Page.end_cursor`).
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
        return build_page(
            self._transport.execute(
                QUERY_SEGMENTS,
                ttd_auth=ttd_auth,
                variables=variables,
                retries=retries,
                timeout_ms=timeout_ms,
                http_headers=http_headers,
            ),
            *SEGMENTS_PATH,
        )

    def query_segment_taxonomy_status(
        self,
        *,
        ttd_auth: Optional[str] = None,
        provider_id: str,
        provider_element_id: str,
        retries: OptionalNullable[RetryConfig] = UNSET,
        timeout_ms: Optional[int] = None,
        http_headers: Optional[Mapping[str, str]] = None,
    ) -> Optional[str]:
        """
        Query the taxonomy compliance approval status of one segment —
        APPROVED, DENIED, PENDING or NOT_IN_QUEUE, matching the REST enum.

        Returns None when the provider has no such segment. Use
        `query_segments` when you need the rest of the segment's fields.

        :param ttd_auth: Platform API token. Defaults to the client's
            configured credential; pass to use a different token for this
            call only.
        """
        page = build_page(
            self._transport.execute(
                QUERY_TAXONOMY_STATUS,
                ttd_auth=ttd_auth,
                variables={
                    "providerId": provider_id,
                    "where": {"providerElementId": {"eq": provider_element_id}},
                },
                retries=retries,
                timeout_ms=timeout_ms,
                http_headers=http_headers,
            ),
            *SEGMENTS_PATH,
        )
        if not page.nodes:
            return None
        return page.nodes[0].get("taxonomyApprovalStatus")
