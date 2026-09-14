from ttd_data.graphql._response import (
    GraphQLError,
    MutationResult,
    Page,
    UpsertResult,
)
from ttd_data.graphql._transport import GraphQLTransport
from ttd_data.graphql.rates import QUERY_DOCUMENTS as _RATES_DOCUMENTS
from ttd_data.graphql.rates import DataRateInput, DataRateOperations
from ttd_data.graphql.taxonomy import QUERY_DOCUMENTS as _TAXONOMY_DOCUMENTS
from ttd_data.graphql.taxonomy import SegmentInput, TaxonomyOperations

# Every document the typed methods send, keyed by method name. The schema
# validator reads this so it can never drift from what callers actually send.
QUERY_DOCUMENTS = {**_TAXONOMY_DOCUMENTS, **_RATES_DOCUMENTS}

__all__ = [
    "DataRateInput",
    "DataRateOperations",
    "GraphQLError",
    "GraphQLTransport",
    "MutationResult",
    "Page",
    "SegmentInput",
    "TaxonomyOperations",
    "UpsertResult",
    "QUERY_DOCUMENTS",
]
