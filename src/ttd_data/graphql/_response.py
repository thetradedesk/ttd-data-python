"""Response envelopes for the typed GraphQL operations.

These model the *envelope* — the `data`/`errors` wrapper and the Relay
connection shape — not the fields inside each node. The envelope is fixed by
the Relay spec and by our own query documents, so it cannot drift when the
schema gains or renames a segment field; node contents stay plain dicts, and
`raw` always carries the untouched body.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from ttd_data.errors import DataError


class GraphQLError(DataError):
    """Top-level `errors` in a GraphQL response.

    Raised even on HTTP 200, which is how the supergraph reports authorization
    and policy failures. `data` carries whatever did resolve, since GraphQL can
    return both. Derives from `DataError` so one `except` covers both suites.
    """

    def __init__(
        self,
        errors: List[Dict[str, Any]],
        raw_response: httpx.Response,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        messages = "; ".join(e.get("message", "") for e in errors) or "unknown error"
        super().__init__(messages, raw_response)
        self.errors = errors
        self.data = data


@dataclass(frozen=True)
class Page:
    """One page of a Relay connection."""

    nodes: List[Dict[str, Any]] = field(default_factory=list)
    total_count: Optional[int] = None
    end_cursor: Optional[str] = None
    has_next_page: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UpsertResult:
    """Outcome of a segment upsert, which succeeds per segment rather than
    all-or-nothing. `failed` being non-empty is the only signal that part of
    the batch was rejected.
    """

    succeeded: List[Dict[str, Any]] = field(default_factory=list)
    """Accepted segments, each entry carrying `mode` (CREATE/UPDATE) and `segment`."""

    failed: List[Dict[str, Any]] = field(default_factory=list)
    """Per-segment rejections, each carrying a `reason` and the identifiers."""

    raw: Dict[str, Any] = field(default_factory=dict)


def _resolve(raw: Dict[str, Any], *path: str) -> Dict[str, Any]:
    """Walk `path` under `data`, yielding `{}` at the first missing or null link."""
    node: Any = raw.get("data") or {}
    for key in path:
        node = (node or {}).get(key) or {}
    return node


def build_page(raw: Dict[str, Any], *path: str) -> Page:
    """Unwrap the connection at `path` under `data` into a `Page`.

    `path` mirrors the selection in the document that produced `raw`; a missing
    or null link along it yields an empty page rather than raising, so a body
    that does not match the document degrades instead of throwing. Denials do
    not arrive this way: the connection fields are non-null, so they surface as
    top-level errors and raise in the transport.
    """
    node = _resolve(raw, *path)
    page_info = node.get("pageInfo") or {}
    return Page(
        nodes=node.get("nodes") or [],
        total_count=node.get("totalCount"),
        end_cursor=page_info.get("endCursor"),
        has_next_page=bool(page_info.get("hasNextPage")),
        raw=raw,
    )


def build_upsert_result(raw: Dict[str, Any], *path: str) -> UpsertResult:
    """Split the mutation payload at `path` into accepted and rejected entries."""
    payload = _resolve(raw, *path)
    return UpsertResult(
        succeeded=payload.get("data") or [],
        failed=payload.get("errors") or [],
        raw=raw,
    )
