"""Example: third-party data taxonomy GraphQL operations via
ttd-data-python's DataClient.

    TTD_AUTH_TOKEN=...              required. Platform token, sent as `TTD-Auth`.
    GRAPHQL_EXAMPLE_PROVIDER_ID=... required. Provider to operate on.
    GRAPHQL_EXAMPLE_ELEMENT_ID=...  optional. Segment to operate on.

Nothing is guessed: every operation acts on exactly what you name. Without
GRAPHQL_EXAMPLE_ELEMENT_ID the file lists segments and runs the escape-hatch
query only. With it, it also reads that segment's approval status, filters to
it, and upserts it — which creates or updates it in the provider's taxonomy.

    TTD_AUTH_TOKEN=... GRAPHQL_EXAMPLE_PROVIDER_ID=... \
      python examples/graphql_example.py
"""

import json
import os

from ttd_data import DataClient
from ttd_data.graphql import Page


def required(name: str, description: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Set {name} to {description}.")
    return value


token = required("TTD_AUTH_TOKEN", "a platform token")
PROVIDER_ID = required("GRAPHQL_EXAMPLE_PROVIDER_ID", "the provider to operate on")

# Optional: the upsert is skipped entirely when this is unset.
ELEMENT_ID = os.getenv("GRAPHQL_EXAMPLE_ELEMENT_ID", "").strip()

client = DataClient(ttd_auth=token)


def show(label: str, page: Page) -> None:
    print(f"\n{'=' * 60}\n  {label}  ({page.total_count} total)\n{'=' * 60}")
    print(json.dumps(page.nodes, indent=2))


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------

segments = client.third_party_taxonomy.query_segments(
    provider_id=PROVIDER_ID, first=5
)
show("Segments for provider", segments)

if segments.has_next_page:
    show(
        "Segments (next page)",
        client.third_party_taxonomy.query_segments(
            provider_id=PROVIDER_ID,
            first=5,
            after=segments.end_cursor,
        ),
    )

if not ELEMENT_ID:
    print("\nSkipping status and filter (set GRAPHQL_EXAMPLE_ELEMENT_ID to run them).")
else:
    status = client.third_party_taxonomy.query_segment_taxonomy_status(
        provider_id=PROVIDER_ID, provider_element_id=ELEMENT_ID
    )
    print(f"\nTaxonomy approval status for {ELEMENT_ID}: {status}")
    show(
        f"Segments filtered to {ELEMENT_ID}",
        client.third_party_taxonomy.query_segments(
            provider_id=PROVIDER_ID, provider_element_ids=[ELEMENT_ID]
        ),
    )

# ---------------------------------------------------------------------------
# Escape hatch: anything the typed methods do not cover
# ---------------------------------------------------------------------------

# `execute` returns the raw body — the typed methods are what wrap it.
raw = client.graphql.execute(
    query="""
    query ThirdPartyDataProvider($id: ID!) {
      thirdPartyDataProvider(id: $id) {
        id
        name
      }
    }
    """,
    variables={"id": PROVIDER_ID},
)
print(f"\n{'=' * 60}\n  Arbitrary query via execute()\n{'=' * 60}")
print(json.dumps(raw.get("data"), indent=2))

# ---------------------------------------------------------------------------
# Mutation — this writes to the provider's taxonomy
# ---------------------------------------------------------------------------

if not ELEMENT_ID:
    print("\nSkipping upsert (set GRAPHQL_EXAMPLE_ELEMENT_ID to run it).")
else:
    result = client.third_party_taxonomy.upsert_segments(
        segments=[
            {
                "providerId": PROVIDER_ID,
                "providerElementId": ELEMENT_ID,
                "displayName": "Example > SDK Test Segment",
                "parentElementId": "ROOT",
                "buyable": True,
                "description": "Created by examples/graphql_example.py",
            }
        ],
    )
    print(f"\n{'=' * 60}\n  Upsert segment\n{'=' * 60}")
    print(f"accepted: {json.dumps(result.succeeded, indent=2)}")
    if result.failed:
        print(f"rejected: {json.dumps(result.failed, indent=2)}")
