"""Live end-to-end test for `ttd_data.DataClient` against TTD's
UID2-aware endpoints.

Each call sends a UID2AdvertiserDataItem-style payload with `email=...`;
the client resolves it via UID2 `POST /identity/map` and forwards a
TDID/UID2-only request to TTD.

Endpoints exercised:
  1. ingest_advertiser_data
  2. ingest_third_party_data
  3. ingest_offline_conversion_data
  4. data_subject_request_advertiser_data
  5. data_subject_request_merchant_data
  6. data_subject_request_third_party_data

Fill in CONFIG below, then run:
    python data-api-local/local_uid2_ingest_e2e.py

Notes:
  - UID2 integ env URL: https://operator-integ.uidapi.com (prod: https://prod.uidapi.com).
  - The TTD Data API call hits the real ingestion endpoint. Use a test
    advertiser/data-provider/merchant ID you have permission to write to.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from ttd_data import errors
from ttd_data._hooks.types import BeforeRequestContext, BeforeRequestHook
from ttd_data.models import AdvertiserData, ThirdPartyData, PartnerDsrRequestType
from ttd_data import DataClient, IdentityScope, UID2Config, UserIdType
from ttd_data.uid2 import (
    AdvertiserDataItem,
    OfflineConversionDataItem,
    PartnerDsrDataItem,
    ThirdPartyDataItem,
)


# ---------------------------------------------------------------------------
# CONFIG — fill these in
# ---------------------------------------------------------------------------

# Secrets and per-account identifiers come from the environment — source
# `.env.local` (see `.env.example`) before running this script.
UID2_BASE_URL = os.getenv("UID2_BASE_URL", "")
UID2_API_KEY = os.getenv("UID2_API_KEY", "")
UID2_CLIENT_SECRET = os.getenv("UID2_CLIENT_SECRET", "")

TTD_DATA_SERVER_URL = os.getenv("TTD_DATA_SERVER_URL", "")
TTD_AUTH_TOKEN = os.getenv("TTD_AUTH_TOKEN", "")
ADVERTISER_ID = os.getenv("TEST_ADVERTISER_ID", "")
DATA_PROVIDER_ID = os.getenv("TEST_DATA_PROVIDER_ID", "")
MERCHANT_ID = int(os.getenv("TEST_MERCHANT_ID", "0"))
TRACKING_TAG_ID = os.getenv("TEST_TRACKING_TAG_ID", "")

# Segment names (only used by the ingest endpoints; DSR doesn't carry data)
ADVERTISER_SEGMENT = "uid2_resolver_smoke_test"
THIRD_PARTY_SEGMENT = "uid2_resolver_smoke_test"

# Test identifiers
RAW_EMAIL = "test129863@example.com"
HASHED_EMAIL = "tMmiiTI7IaAcPpQPFQ65uMVCWH8av9jw4cwf/F5HVRQ="  # sha256(b"test@example.com").b64
OPTOUT_EMAIL = "optout123@unifiedid.com"
RAW_PHONE = "+15551234567"
HASHED_PHONE = "F0snlcSt7L9QYTm3l1Q3p+sjBWUyOj9MnSDvSiTrPyU="  # sha256(b"+15551234567").b64
PASSTHROUGH_TDID = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _section(title: str) -> None:
    bar = "=" * 70
    print(f"\n{bar}\n  {title}\n{bar}")


def _print_items(label: str, items: list) -> None:
    print(f"\n{label}:")
    for i, item in enumerate(items):
        print(f"  [{i}] {item.model_dump(by_alias=True, exclude_none=True)}")


def _print_response(label: str, response: Any, server_attr: str) -> None:
    print(f"\n{label}:")
    server_response = getattr(response, server_attr, None)
    failed_lines = getattr(server_response, "failed_lines", None) if server_response else None
    if failed_lines:
        print(f"  failed_lines ({len(failed_lines)}):")
        for line in failed_lines:
            print(
                f"    item_number={getattr(line, 'item_number', None)} "
                f"error_code={getattr(line, 'error_code', None)} "
                f"message={getattr(line, 'message', None)!r}"
            )
    else:
        print("  no failed lines")

    print("\n  identity_resolutions:")
    for raw_id, resolution in response.identity_resolutions.items():
        print(f"    {raw_id}")
        print(f"      current_raw_uid : {resolution.current_raw_uid}")
        print(f"      previous_raw_uid: {resolution.previous_raw_uid}")
        print(f"      refresh_from    : {resolution.refresh_from}")
        print(f"      unmapped_reason : {resolution.unmapped_reason}")


_REDACT_HEADERS = {"ttd-auth", "authorization", "ttdsignature"}


class _RawRequestPrinter(BeforeRequestHook):
    """Logs method, URL, headers (sensitive values redacted) and body of every
    outgoing HTTP request right before httpx sends it."""

    def before_request(
        self, hook_ctx: BeforeRequestContext, request: httpx.Request
    ) -> httpx.Request:
        print(f"\n  --- raw request ({hook_ctx.operation_id}) ---")
        print(f"  {request.method} {request.url}")
        print("  headers:")
        for k, v in request.headers.items():
            redacted = "<redacted>" if k.lower() in _REDACT_HEADERS else v
            print(f"    {k}: {redacted}")
        body = request.content
        try:
            body_str = body.decode("utf-8") if isinstance(body, bytes) else str(body)
        except UnicodeDecodeError:
            body_str = repr(body)
        print(f"  body ({len(body)} bytes): {body_str}")
        print("  --- end raw request ---")
        return request


def _run(name: str, action: Callable[[], None]) -> None:
    """Run one endpoint's exercise inside a unified error-printing wrapper."""
    _section(name)
    try:
        action()
    except errors.DataError as exc:  # base class for all speakeasy-mapped errors
        print(f"\nServer error: {getattr(exc, 'message', exc)}")
        if hasattr(exc, "status_code"):
            print(f"status: {exc.status_code}")
        data = getattr(exc, "data", None)
        if data is not None and getattr(data, "failed_lines", None):
            print(f"failed_lines: {data.failed_lines}")


class _RequestBodyCapture(BeforeRequestHook):
    """Captures the raw serialized request body for post-call assertions."""

    def __init__(self) -> None:
        self.bodies: list[str] = []

    def before_request(
        self, hook_ctx: BeforeRequestContext, request: httpx.Request
    ) -> httpx.Request:
        try:
            self.bodies.append(request.content.decode("utf-8"))
        except UnicodeDecodeError:
            self.bodies.append(repr(request.content))
        return request

    def assert_absent(self, *strings: str) -> None:
        leaked: list[str] = []
        for body in self.bodies:
            for s in strings:
                if s in body:
                    leaked.append(f"  {s!r} found in body: {body[:300]!r}")
        if leaked:
            raise AssertionError(
                "PII strings found in outbound request body:\n" + "\n".join(leaked)
            )
        print(f"  PASS: {strings} absent from all {len(self.bodies)} captured request(s)")


# ---------------------------------------------------------------------------
# Endpoint exercises
# ---------------------------------------------------------------------------


def exercise_advertiser_ingest(client: DataClient) -> None:
    # Expected outcomes per item under collect-all mode:
    #   [0] email resolves → UID2 set, line accepted.
    #   [1] hashed_email resolves → UID2 set, line accepted.
    #   [2] optout email → UID2='*' substituted; the Trade Desk Data APIs reject
    #       (no fallback) → failed_lines entry with ErrorCode=Uid2Error (merged
    #       from failed_mappings).
    #   [3] TDID passthrough → no UID2 work, line accepted.
    #   [4] optout email + valid TDID: UID2='*' substituted, but the Trade Desk
    #       Data APIs accept on TDID via first-valid-wins. No failed_lines entry.
    items = [
        AdvertiserDataItem(data=[AdvertiserData(name=ADVERTISER_SEGMENT)], email=RAW_EMAIL),
        AdvertiserDataItem(data=[AdvertiserData(name=ADVERTISER_SEGMENT)], hashed_email=HASHED_EMAIL),
        AdvertiserDataItem(data=[AdvertiserData(name=ADVERTISER_SEGMENT)], email=OPTOUT_EMAIL),
        AdvertiserDataItem(data=[AdvertiserData(name=ADVERTISER_SEGMENT)], tdid=PASSTHROUGH_TDID),
        AdvertiserDataItem(
            data=[AdvertiserData(name=ADVERTISER_SEGMENT)],
            email=OPTOUT_EMAIL,
            tdid=PASSTHROUGH_TDID,
        ),
    ]
    _print_items("Submitting items", items)
    response = client.advertiser.ingest_advertiser_data(
        advertiser_id=ADVERTISER_ID,
        ttd_auth=TTD_AUTH_TOKEN,
        items=items,
    )
    _print_items("Items after resolution", items)
    _print_response("TTD response", response, "advertiser_data_server_response")


def exercise_third_party_ingest(client: DataClient) -> None:
    # Same expected outcomes as exercise_advertiser_ingest — third-party handler
    # uses the same first-valid-wins priority chain, so item [4] (optout +
    # fallback TDID) is accepted on TDID.
    items = [
        ThirdPartyDataItem(data=[ThirdPartyData(name=THIRD_PARTY_SEGMENT)], email=RAW_EMAIL),
        ThirdPartyDataItem(data=[ThirdPartyData(name=THIRD_PARTY_SEGMENT)], hashed_email=HASHED_EMAIL),
        ThirdPartyDataItem(data=[ThirdPartyData(name=THIRD_PARTY_SEGMENT)], email=OPTOUT_EMAIL),
        ThirdPartyDataItem(data=[ThirdPartyData(name=THIRD_PARTY_SEGMENT)], tdid=PASSTHROUGH_TDID),
        ThirdPartyDataItem(
            data=[ThirdPartyData(name=THIRD_PARTY_SEGMENT)],
            email=OPTOUT_EMAIL,
            tdid=PASSTHROUGH_TDID,
        ),
    ]
    _print_items("Submitting items", items)
    response = client.third_party.ingest_third_party_data(
        data_provider_id=DATA_PROVIDER_ID,
        ttd_auth=TTD_AUTH_TOKEN,
        items=items,
    )
    _print_items("Items after resolution", items)
    _print_response("TTD response", response, "third_party_data_server_response")


def exercise_offline_conversion_ingest(client: DataClient) -> None:
    # Expected outcomes per item under collect-all mode:
    #   [0]–[3] same shape as advertiser: resolve / resolve / optout-no-fallback /
    #       TDID passthrough.
    #   [4] UserIdArray with two resolvable entries — both rewritten in place to
    #       ["2", uid2]; line accepted.
    #   [5] optout email + TDID fallback: UID2='*', the Trade Desk Data APIs'
    #       offline conversion priority chain falls through to TDID. No
    #       failed_lines entry.
    #   [6] UserIdArray containing an optout email at -3. The Trade Desk Data APIs'
    #       TryParseUserIdArray rejects the whole line on the first invalid
    #       entry — failed_lines entry expected with ErrorCode=Uid2Error.
    now = datetime.now(timezone.utc)
    items = [
        OfflineConversionDataItem(tracking_tag_id=TRACKING_TAG_ID, timestamp_utc=now, email=RAW_EMAIL),
        OfflineConversionDataItem(tracking_tag_id=TRACKING_TAG_ID, timestamp_utc=now, hashed_email=HASHED_EMAIL),
        OfflineConversionDataItem(tracking_tag_id=TRACKING_TAG_ID, timestamp_utc=now, email=OPTOUT_EMAIL),
        OfflineConversionDataItem(tracking_tag_id=TRACKING_TAG_ID, timestamp_utc=now, tdid=PASSTHROUGH_TDID),
        OfflineConversionDataItem(
            tracking_tag_id=TRACKING_TAG_ID,
            timestamp_utc=now,
            user_id_array=[[UserIdType.HASHED_EMAIL, HASHED_EMAIL], [UserIdType.EMAIL, RAW_EMAIL]],
        ),
        OfflineConversionDataItem(
            tracking_tag_id=TRACKING_TAG_ID,
            timestamp_utc=now,
            email=OPTOUT_EMAIL,
            tdid=PASSTHROUGH_TDID,
        ),
        OfflineConversionDataItem(
            tracking_tag_id=TRACKING_TAG_ID,
            timestamp_utc=now,
            user_id_array=[[UserIdType.EMAIL, OPTOUT_EMAIL]],
        ),
    ]
    _print_items("Submitting items", items)
    response = client.offline_conversion.ingest_offline_conversion_data(
        ttd_auth=TTD_AUTH_TOKEN,
        data_provider_id=DATA_PROVIDER_ID,
        items=items,
        user_id_array_metadata_format=["type", "id"],
    )
    _print_items("Items after resolution", items)
    _print_response("TTD response", response, "offline_conversion_data_server_response")


def exercise_dsr_advertiser(client: DataClient) -> None:
    # Expected outcomes per item:
    #   [0] email resolves → UID2 set, line accepted.
    #   [1] TDID passthrough → line accepted.
    #   [2] optout email (no fallback) → UID2='*', the Trade Desk Data APIs
    #       reject, merged to ErrorCode=Uid2Error.
    #   [3] optout email + TDID fallback: line accepted on TDID.
    items = [
        PartnerDsrDataItem(email=RAW_EMAIL),
        PartnerDsrDataItem(tdid=PASSTHROUGH_TDID),
        PartnerDsrDataItem(email=OPTOUT_EMAIL),
        PartnerDsrDataItem(email=OPTOUT_EMAIL, tdid=PASSTHROUGH_TDID),
    ]
    _print_items("Submitting items", items)
    response = client.deletion_opt_out.data_subject_request_advertiser_data(
        advertiser_id=ADVERTISER_ID,
        ttd_auth=TTD_AUTH_TOKEN,
        items=items,
        request_type=PartnerDsrRequestType.OPT_OUT,
    )
    _print_items("Items after resolution", items)
    _print_response("TTD response", response, "advertiser_dsr_response")


def exercise_dsr_merchant(client: DataClient) -> None:
    # Expected outcomes per item:
    #   [0] email resolves → UID2 set, line accepted.
    #   [1] TDID passthrough → line accepted.
    #   [2] optout email (no fallback) → UID2='*', the Trade Desk Data APIs
    #       reject, merged to ErrorCode=Uid2Error.
    #   [3] optout email + TDID fallback: line accepted on TDID.
    items = [
        PartnerDsrDataItem(email=RAW_EMAIL),
        PartnerDsrDataItem(tdid=PASSTHROUGH_TDID),
        PartnerDsrDataItem(email=OPTOUT_EMAIL),
        PartnerDsrDataItem(email=OPTOUT_EMAIL, tdid=PASSTHROUGH_TDID),
    ]
    _print_items("Submitting items", items)
    response = client.deletion_opt_out.data_subject_request_merchant_data(
        merchant_id=MERCHANT_ID,
        ttd_auth=TTD_AUTH_TOKEN,
        items=items,
        request_type=PartnerDsrRequestType.OPT_OUT,
    )
    _print_items("Items after resolution", items)
    _print_response("TTD response", response, "merchant_dsr_response")


def exercise_dsr_third_party(client: DataClient) -> None:
    # Expected outcomes per item:
    #   [0] email resolves → UID2 set, line accepted.
    #   [1] TDID passthrough → line accepted.
    #   [2] optout email (no fallback) → UID2='*', the Trade Desk Data APIs
    #       reject, merged to ErrorCode=Uid2Error.
    #   [3] optout email + TDID fallback: line accepted on TDID.
    items = [
        PartnerDsrDataItem(email=RAW_EMAIL),
        PartnerDsrDataItem(tdid=PASSTHROUGH_TDID),
        PartnerDsrDataItem(email=OPTOUT_EMAIL),
        PartnerDsrDataItem(email=OPTOUT_EMAIL, tdid=PASSTHROUGH_TDID),
    ]
    _print_items("Submitting items", items)
    response = client.deletion_opt_out.data_subject_request_third_party_data(
        data_provider_id=DATA_PROVIDER_ID,
        ttd_auth=TTD_AUTH_TOKEN,
        items=items,
        request_type=PartnerDsrRequestType.OPT_OUT,
    )
    _print_items("Items after resolution", items)
    _print_response("TTD response", response, "third_party_dsr_response")


# ---------------------------------------------------------------------------
# PII dropping checks
# ---------------------------------------------------------------------------


def _make_uid2_client() -> DataClient:
    config = UID2Config(
        base_url=UID2_BASE_URL,
        api_key=UID2_API_KEY,
        client_secret=UID2_CLIENT_SECRET,
        identity_scope=IdentityScope.UID2,
    )
    return DataClient(config, server_url=TTD_DATA_SERVER_URL)


def _register_capture(client: DataClient) -> _RequestBodyCapture:
    capture = _RequestBodyCapture()
    hooks = client.data_client.sdk_configuration.__dict__["_hooks"]
    hooks.register_before_request_hook(capture)
    return capture


def verify_pii_not_in_request_with_uid2_config() -> None:
    """After UID2 resolution the raw email / hashed_email must not appear in
    the HTTP body sent to DataServer.

    The resolver writes the resolved UID2 token onto each item and calls
    _clear_extras to zero the raw identifier fields before the speakeasy
    serializer touches the items.
    """
    client = _make_uid2_client()
    capture = _register_capture(client)

    items = [
        AdvertiserDataItem(data=[AdvertiserData(name=ADVERTISER_SEGMENT)], email=RAW_EMAIL),
        AdvertiserDataItem(data=[AdvertiserData(name=ADVERTISER_SEGMENT)], hashed_email=HASHED_EMAIL),
        AdvertiserDataItem(data=[AdvertiserData(name=ADVERTISER_SEGMENT)], tdid=PASSTHROUGH_TDID),
    ]
    _print_items("Submitting items", items)
    try:
        response = client.advertiser.ingest_advertiser_data(
            advertiser_id=ADVERTISER_ID,
            ttd_auth=TTD_AUTH_TOKEN,
            items=items,
        )
        _print_response("TTD response", response, "advertiser_data_server_response")
    except Exception as exc:
        print(f"  (server call: {exc.__class__.__name__}: {exc})")

    capture.assert_absent(RAW_EMAIL, HASHED_EMAIL)


def verify_pii_not_in_request_no_uid2_config() -> None:
    """Even without a UID2Config, raw email / phone must not appear in the HTTP
    body sent to DataServer.

    No UID2 resolution runs, but the wrapper-to-base model_validate conversion
    still drops Email / Phone / HashedEmail / HashedPhone because
    BaseAdvertiserDataItem has no such fields — pydantic silently ignores them.
    """
    # No uid2_config — UID2 resolution is intentionally skipped.
    client = DataClient(server_url=TTD_DATA_SERVER_URL)
    capture = _register_capture(client)

    items = [
        AdvertiserDataItem(data=[AdvertiserData(name=ADVERTISER_SEGMENT)], email=RAW_EMAIL),
        AdvertiserDataItem(data=[AdvertiserData(name=ADVERTISER_SEGMENT)], hashed_email=HASHED_EMAIL),
        AdvertiserDataItem(data=[AdvertiserData(name=ADVERTISER_SEGMENT)], tdid=PASSTHROUGH_TDID),
    ]
    _print_items("Submitting items (no UID2 config)", items)
    try:
        response = client.advertiser.ingest_advertiser_data(
            advertiser_id=ADVERTISER_ID,
            ttd_auth=TTD_AUTH_TOKEN,
            items=items,
        )
        _print_response("TTD response", response, "advertiser_data_server_response")
    except Exception as exc:
        print(f"  (server call: {exc.__class__.__name__}: {exc})")

    capture.assert_absent(RAW_EMAIL, HASHED_EMAIL)


def verify_user_id_array_pii_not_in_request_no_uid2_config() -> None:
    """Without a UID2Config, raw PII inside `user_id_array` entries must not
    appear in the HTTP body sent to DataServer. The resolver-free path
    (`mark_raw_pii_failures_without_uid2`) substitutes the UID2 sentinel `*`
    into each offending slot before serialization.
    """
    client = DataClient(server_url=TTD_DATA_SERVER_URL)
    capture = _register_capture(client)

    now = datetime.now(timezone.utc)
    items = [
        OfflineConversionDataItem(
            tracking_tag_id=TRACKING_TAG_ID,
            timestamp_utc=now,
            user_id_array=[
                [UserIdType.EMAIL, RAW_EMAIL],
                [UserIdType.HASHED_EMAIL, HASHED_EMAIL],
                [UserIdType.PHONE, RAW_PHONE],
                [UserIdType.HASHED_PHONE, HASHED_PHONE],
            ],
        ),
        OfflineConversionDataItem(
            tracking_tag_id=TRACKING_TAG_ID,
            timestamp_utc=now,
            user_id_array=[[UserIdType.TDID, PASSTHROUGH_TDID]],
        ),
    ]
    _print_items("Input items (no UID2 config, user_id_array)", items)
    try:
        response = client.offline_conversion.ingest_offline_conversion_data(
            ttd_auth=TTD_AUTH_TOKEN,
            data_provider_id=DATA_PROVIDER_ID,
            items=items,
            user_id_array_metadata_format=["type", "id"],
        )
        _print_items("Items sent to TTD Data API (post-resolution)", items)
        _print_response(
            "TTD response", response, "offline_conversion_data_server_response"
        )
    except Exception as exc:
        print(f"  (server call: {exc.__class__.__name__}: {exc})")

    capture.assert_absent(RAW_EMAIL, HASHED_EMAIL, RAW_PHONE, HASHED_PHONE)


def verify_user_id_array_pii_not_in_request_with_uid2_config() -> None:
    """With a UID2Config, raw PII inside `user_id_array` entries gets resolved
    by `POST /identity/map` and the slot is rewritten to `[UID2, <token>]`
    (or `[UID2, "*"]` for unmapped/optout). The raw values must not appear
    on the outbound wire.
    """
    client = _make_uid2_client()
    capture = _register_capture(client)

    now = datetime.now(timezone.utc)
    items = [
        OfflineConversionDataItem(
            tracking_tag_id=TRACKING_TAG_ID,
            timestamp_utc=now,
            user_id_array=[
                [UserIdType.EMAIL, RAW_EMAIL],
                [UserIdType.HASHED_EMAIL, HASHED_EMAIL],
                [UserIdType.PHONE, RAW_PHONE],
                [UserIdType.HASHED_PHONE, HASHED_PHONE],
            ],
        ),
        OfflineConversionDataItem(
            tracking_tag_id=TRACKING_TAG_ID,
            timestamp_utc=now,
            user_id_array=[[UserIdType.TDID, PASSTHROUGH_TDID]],
        ),
    ]
    _print_items("Input items (with UID2 config, user_id_array)", items)
    try:
        response = client.offline_conversion.ingest_offline_conversion_data(
            ttd_auth=TTD_AUTH_TOKEN,
            data_provider_id=DATA_PROVIDER_ID,
            items=items,
            user_id_array_metadata_format=["type", "id"],
        )
        _print_items("Items sent to TTD Data API (post-resolution)", items)
        _print_response(
            "TTD response", response, "offline_conversion_data_server_response"
        )
    except Exception as exc:
        print(f"  (server call: {exc.__class__.__name__}: {exc})")

    capture.assert_absent(RAW_EMAIL, HASHED_EMAIL, RAW_PHONE, HASHED_PHONE)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main() -> None:
    config = UID2Config(
        base_url=UID2_BASE_URL,
        api_key=UID2_API_KEY,
        client_secret=UID2_CLIENT_SECRET,
        identity_scope=IdentityScope.UID2,
    )
    client = DataClient(config, server_url=TTD_DATA_SERVER_URL)

    # `_hooks` is a private attribute on the speakeasy SDK config; `register_before_request_hook`
    # appends to its hook list so all subsequent requests run through it.
    hooks = client.data_client.sdk_configuration.__dict__["_hooks"]
    hooks.register_before_request_hook(_RawRequestPrinter())

    _run("Advertiser ingest", lambda: exercise_advertiser_ingest(client))
    _run("Third-party ingest", lambda: exercise_third_party_ingest(client))
    _run("Offline conversion ingest", lambda: exercise_offline_conversion_ingest(client))
    _run("DSR — advertiser", lambda: exercise_dsr_advertiser(client))
    _run("DSR — merchant", lambda: exercise_dsr_merchant(client))
    _run("DSR — third-party", lambda: exercise_dsr_third_party(client))
    _run("PII dropping checks — with UID2 config", verify_pii_not_in_request_with_uid2_config)
    _run("PII dropping checks — no UID2 config", verify_pii_not_in_request_no_uid2_config)
    _run(
        "PII dropping checks — user_id_array present without UID2 config",
        verify_user_id_array_pii_not_in_request_no_uid2_config,
    )
    _run(
        "PII dropping checks — user_id_array present with UID2 config",
        verify_user_id_array_pii_not_in_request_with_uid2_config,
    )


if __name__ == "__main__":
    main()
