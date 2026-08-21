"""Validates every GraphQL document the SDK sends against the Impala
subgraph SDL. Offline: no network calls. This is the check that catches a
field name that does not exist before a caller ever sends one over the wire.

Opt-in only: the SDL is never committed to this (public) repo — it carries
internal feature-flag/permission names, tenant-specific policy, and staff
email addresses from deprecation directives. Point TTD_GRAPHQL_SCHEMA_PATH at
a local copy (see `scripts/validate_graphql.py --write-sdl`) to run this;
otherwise it skips, and `scripts/validate_graphql.py` run against the live
endpoint is the equivalent on-demand check.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

graphql = pytest.importorskip("graphql")

_DEFAULT_SDL_PATH = Path(__file__).resolve().parents[2] / "impala.graphql"
SDL_PATH = Path(os.environ.get("TTD_GRAPHQL_SCHEMA_PATH", _DEFAULT_SDL_PATH))


@pytest.fixture(scope="module")
def schema():
    if not SDL_PATH.exists():
        pytest.skip(f"{SDL_PATH} not present (set TTD_GRAPHQL_SCHEMA_PATH to enable)")
    # assume_valid: the SDL is a federation subgraph whose @key/@override/
    # @policy directives are supplied by @link, not declared in the file.
    return graphql.build_schema(
        SDL_PATH.read_text(encoding="utf-8"),
        assume_valid=True,
        assume_valid_sdl=True,
    )


def _document_names():
    from ttd_data.graphql import QUERY_DOCUMENTS

    return sorted(QUERY_DOCUMENTS)


@pytest.mark.parametrize("name", _document_names())
def test_document_is_valid_against_schema(schema, name):
    from ttd_data.graphql import QUERY_DOCUMENTS

    errors = graphql.validate(schema, graphql.parse(QUERY_DOCUMENTS[name]))
    assert not errors, "\n".join(error.message for error in errors)


def test_every_typed_method_has_a_registered_document():
    """Guards the validator's coverage: a new typed method that forgets to
    register its document would otherwise never be schema-checked. Add each
    new operation class here alongside its QUERY_DOCUMENTS entries."""
    from ttd_data.graphql import QUERY_DOCUMENTS, TaxonomyOperations

    operation_classes = [TaxonomyOperations]
    typed_methods = {
        name
        for cls in operation_classes
        for name in dir(cls)
        if name.startswith(("query_", "upsert_")) and callable(getattr(cls, name))
    }
    assert typed_methods == set(QUERY_DOCUMENTS)
