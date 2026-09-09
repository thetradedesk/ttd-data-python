from ttd_data.graphql._response import GraphQLError, Page, UpsertResult
from ttd_data.graphql._transport import GraphQLTransport
from ttd_data.graphql.taxonomy import QUERY_DOCUMENTS as _TAXONOMY_DOCUMENTS
from ttd_data.graphql.taxonomy import SegmentInput, TaxonomyOperations

# Every document the typed methods send, keyed by method name. The schema
# validator reads this so it can never drift from what callers actually send.
QUERY_DOCUMENTS = dict(_TAXONOMY_DOCUMENTS)

__all__ = [
    "GraphQLError",
    "GraphQLTransport",
    "Page",
    "SegmentInput",
    "TaxonomyOperations",
    "UpsertResult",
    "QUERY_DOCUMENTS",
]
