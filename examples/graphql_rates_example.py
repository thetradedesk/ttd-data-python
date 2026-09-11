"""Example: third-party data rate GraphQL operations via ttd-data-python's
DataClient.

    TTD_AUTH_TOKEN=...              required. Platform token, sent as `TTD-Auth`.
    GRAPHQL_EXAMPLE_PROVIDER_ID=... required. Provider to operate on.
    GRAPHQL_EXAMPLE_BRAND_ID=...    optional. Brand to filter rates by.
    GRAPHQL_EXAMPLE_ELEMENT_ID=...  optional. Segment to price.

Reads run unconditionally. The batch submission at the end is a write, and is
skipped unless GRAPHQL_EXAMPLE_ELEMENT_ID and GRAPHQL_EXAMPLE_BRAND_ID are
both set. The submitter is taken from the token's email.

    TTD_AUTH_TOKEN=... GRAPHQL_EXAMPLE_PROVIDER_ID=... \
      python examples/graphql_rates_example.py
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

BRAND_ID = os.getenv("GRAPHQL_EXAMPLE_BRAND_ID", "").strip()
ELEMENT_ID = os.getenv("GRAPHQL_EXAMPLE_ELEMENT_ID", "").strip()

client = DataClient(ttd_auth=token)
rates = client.third_party_data_rate


def show(label: str, page: Page) -> None:
    print(f"\n{'=' * 60}\n  {label}  ({page.total_count} total)\n{'=' * 60}")
    print(json.dumps(page.nodes, indent=2))


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

show(
    "Brands for provider",
    rates.query_brands(provider_id=PROVIDER_ID, first=10),
)

show(
    "Data rates for provider segments",
    rates.query_segment_data_rates(provider_id=PROVIDER_ID, first=5),
)

if not BRAND_ID:
    print("\nSkipping brand filter (set GRAPHQL_EXAMPLE_BRAND_ID to run it).")
else:
    show(
        f"Data rates filtered to brand {BRAND_ID}",
        rates.query_segment_data_rates(
            provider_id=PROVIDER_ID, brand_id=BRAND_ID, first=5
        ),
    )

show(
    "Data rate batches",
    rates.query_data_rate_batches(provider_id=PROVIDER_ID, first=10),
)

# ---------------------------------------------------------------------------
# Mutation — this submits a rate batch against the provider
# ---------------------------------------------------------------------------

if not (ELEMENT_ID and BRAND_ID):
    print(
        "\nSkipping batch submission (needs GRAPHQL_EXAMPLE_ELEMENT_ID "
        "and GRAPHQL_EXAMPLE_BRAND_ID)."
    )
else:
    # Omitting `subject` makes this a system (syndicated) rate.
    result = rates.create_data_rate_batch(
        provider_id=PROVIDER_ID,
        data_rates=[
            {
                "providerElementId": ELEMENT_ID,
                "thirdPartyDataBrandId": BRAND_ID,
                "cost": {"cpm": {"cpmCost": {"amount": 2.5, "currencyCode": "USD"}}},
            }
        ],
    )
    print(f"\n{'=' * 60}\n  Submit data rate batch\n{'=' * 60}")
    if result.data is None:
        print(f"rejected: {json.dumps(result.errors, indent=2)}")
    else:
        print(json.dumps(result.data, indent=2))
        # Queued, not applied: read the batch back to follow its processing.
        show(
            "Submitted batch",
            rates.query_data_rate_batches(
                provider_id=PROVIDER_ID, batch_id=result.data["id"]
            ),
        )
