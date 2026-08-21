#!/usr/bin/env python
"""Validate every GraphQL document the SDK sends against the live schema.

Introspects the Platform API supergraph and validates each document in
`ttd_data.graphql.QUERY_DOCUMENTS`. Requires a platform credential:

    TTD_AUTH_TOKEN=... python scripts/validate_graphql.py

Introspection needs authentication (the endpoint returns 401 without it), so
this runs on demand rather than as a pull-request check.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Tuple

import httpx
from graphql import build_client_schema, get_introspection_query, parse, print_schema, validate

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# pylint: disable=wrong-import-position  # sys.path is set up just above
from ttd_data.graphql import QUERY_DOCUMENTS  # noqa: E402
from ttd_data.graphql import GraphQLTransport  # noqa: E402

HTTP_TIMEOUT_S = 60.0


def resolve_auth_headers() -> Tuple[Dict[str, str], str]:
    """Resolve credentials from the environment. Never returns the token value
    in the description."""
    bearer = os.environ.get("BEARER_TOKEN", "").strip()
    if bearer:
        value = bearer if bearer.lower().startswith("bearer ") else f"Bearer {bearer}"
        return {"Authorization": value}, "BEARER_TOKEN"
    ttd_auth = os.environ.get("TTD_AUTH_TOKEN", "").strip()
    if ttd_auth:
        return {"TTD-Auth": ttd_auth}, "TTD_AUTH_TOKEN"
    return {}, "none"


def fetch_schema(url: str, headers: Dict[str, str]):
    """POST the introspection query and build a client schema from the result."""
    query = get_introspection_query(descriptions=False, directive_is_repeatable=True)
    try:
        response = httpx.post(
            url,
            json={"query": query},
            headers={"Content-Type": "application/json", **headers},
            timeout=HTTP_TIMEOUT_S,
        )
    except httpx.HTTPError as exc:
        sys.exit(f"Failed to reach {url}: {exc}. Check your network/VPN connection.")

    if response.status_code in (401, 403):
        sys.exit(f"Auth rejected ({response.status_code}) by {url}. Refresh your token and retry.")
    if response.status_code != 200:
        sys.exit(f"Introspection failed: HTTP {response.status_code} from {url}.")

    body = response.json()
    if body.get("errors"):
        sys.exit(f"Introspection returned errors: {body['errors']}")
    schema_root = (body.get("data") or {}).get("__schema")
    if not schema_root:
        sys.exit(f"Response from {url} contained no '__schema'.")
    return build_client_schema({"__schema": schema_root})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=GraphQLTransport.DEFAULT_ENDPOINT, help="GraphQL endpoint")
    parser.add_argument("--write-sdl", type=Path, help="Also write the composed SDL here")
    args = parser.parse_args()

    headers, source = resolve_auth_headers()
    if not headers:
        sys.exit("No credentials found. Set TTD_AUTH_TOKEN or BEARER_TOKEN.")

    print(f"Introspecting {args.url} (auth from {source})...", flush=True)
    schema = fetch_schema(args.url, headers)

    if args.write_sdl:
        args.write_sdl.parent.mkdir(parents=True, exist_ok=True)
        args.write_sdl.write_text(print_schema(schema), encoding="utf-8")
        print(f"Wrote SDL to {args.write_sdl}")

    failed = 0
    for name, document in sorted(QUERY_DOCUMENTS.items()):
        errors = validate(schema, parse(document))
        if errors:
            failed += 1
            print(f"\nFAIL {name}")
            for error in errors:
                print(f"  {error.message}")
                if error.locations:
                    location = error.locations[0]
                    print(f"    at line {location.line}, column {location.column}")
        else:
            print(f"ok   {name}")

    total = len(QUERY_DOCUMENTS)
    if failed:
        print(f"\n{failed}/{total} documents failed validation.")
        return 1
    print(f"\nAll {total} documents valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
