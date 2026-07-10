"""Unit tests for the UID2 wrapper layer (`ttd_data.DataClient`, the resolver,
and the at-most-one-identifier validator). No network; the UID2 SDK client
is mocked."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import MagicMock
from urllib.error import HTTPError

import pytest


# ---------------------------------------------------------------------------
# Local test helpers
# ---------------------------------------------------------------------------


def _make_identity_map_client(
    mapped: Dict[str, Any] | None = None,
    unmapped: Dict[str, Any] | None = None,
) -> MagicMock:
    response = SimpleNamespace(
        mapped_identities=mapped or {},
        unmapped_identities=unmapped or {},
    )
    client = MagicMock()
    client.generate_identity_map.return_value = response
    return client


def _mapped(uid: str) -> SimpleNamespace:
    return SimpleNamespace(
        current_raw_uid=uid,
        previous_raw_uid=None,
        refresh_from=None,
    )


def _unmapped(reason: str) -> SimpleNamespace:
    return SimpleNamespace(raw_reason=reason)


def _advertiser_item(**kwargs: Any):
    """`AdvertiserDataItem` with the required `data` field defaulted."""
    from ttd_data.models import AdvertiserData
    from ttd_data.uid2 import AdvertiserDataItem

    return AdvertiserDataItem(data=[AdvertiserData(name="seg")], **kwargs)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def test_public_imports_resolve():
    """Top-level imports a caller is expected to use."""
    from ttd_data import ClientConfig, DataClient, IdentityScope, UID2Config  # noqa: F401
    from ttd_data.uid2 import (  # noqa: F401
        AdvertiserDataItem,
        OfflineConversionDataItem,
        PartnerDsrDataItem,
        ThirdPartyDataItem,
        UID2ServiceError,
    )


def test_config_property_reconstructs_an_equivalent_client():
    from ttd_data import ClientConfig, DataClient, UID2Config
    from ttd_data.uid2 import IdentityScope

    uid2_config = UID2Config(
        base_url="https://uid2.example.com",
        api_key="key",
        client_secret="secret",
        identity_scope=IdentityScope.UID2,
    )
    client = DataClient(
        uid2_config=uid2_config, server_url="https://example.com", timeout_ms=5000
    )

    config = client.config
    assert isinstance(config, ClientConfig)

    rebuilt = DataClient(**config.__dict__)
    assert rebuilt.config == config


def test_client_config_tracks_base_data_client_constructor_params():
    """Fails if a new `BaseDataClient` constructor param is added without
    updating `ClientConfig`."""
    import dataclasses
    import inspect

    from ttd_data.client import ClientConfig
    from ttd_data.sdk import BaseDataClient

    # Exclude live resources from ClientConfig
    not_reconstructable = {"client", "async_client", "debug_logger"}

    base_params = set(inspect.signature(BaseDataClient.__init__).parameters) - {
        "self",
        *not_reconstructable,
    }
    config_fields = {f.name for f in dataclasses.fields(ClientConfig)} - {"uid2_config"}

    assert base_params == config_fields


def test_base_data_client_hidden_from_package_root():
    """Locks in the `from .sdk import *` deletion in `__init__.py`. If a
    future regen re-adds the wildcard, this test fails loudly so we don't
    silently re-expose the internal Speakeasy class."""
    import ttd_data

    assert not hasattr(ttd_data, "BaseDataClient"), (
        "BaseDataClient must not be exported from the package root. "
        "Check that `from .sdk import *` is absent from src/ttd_data/__init__.py."
    )


# ---------------------------------------------------------------------------
# At-most-one UID2-family identifier validator
# ---------------------------------------------------------------------------


def test_item_accepts_single_raw_identifier():
    item = _advertiser_item(email="alice@example.com")
    assert item.email == "alice@example.com"


def test_item_rejects_two_raw_identifiers():
    with pytest.raises(ValueError, match="At most one UID2-family identifier"):
        _advertiser_item(email="alice@example.com", phone="+15551234567")


def test_item_rejects_raw_plus_resolved():
    with pytest.raises(ValueError, match="At most one UID2-family identifier"):
        _advertiser_item(email="alice@example.com", uid2="some-uid2")


# ---------------------------------------------------------------------------
# Resolver — mapped path
# ---------------------------------------------------------------------------


def test_resolver_maps_top_level_email_and_clears_raw():
    from ttd_data.uid2 import IdentityScope
    from ttd_data.uid2.resolver import resolve_uid2_identifiers_in_place

    items = [_advertiser_item(email="alice@example.com")]
    client = _make_identity_map_client(
        mapped={"alice@example.com": _mapped("UID2_ALICE")}
    )

    resolutions, failures = resolve_uid2_identifiers_in_place(
        items, client, IdentityScope.UID2
    )

    assert items[0].uid2 == "UID2_ALICE"
    assert not items[0].email
    assert resolutions["alice@example.com"].current_raw_uid == "UID2_ALICE"
    assert failures == {}


def test_resolver_writes_euid_field_under_euid_scope():
    from ttd_data.uid2 import IdentityScope
    from ttd_data.uid2.resolver import resolve_uid2_identifiers_in_place

    items = [_advertiser_item(email="bob@example.com")]
    client = _make_identity_map_client(
        mapped={"bob@example.com": _mapped("EUID_BOB")}
    )

    resolve_uid2_identifiers_in_place(items, client, IdentityScope.EUID)

    assert items[0].euid == "EUID_BOB"
    assert not items[0].uid2


# ---------------------------------------------------------------------------
# Resolver — unmapped path (sentinel substitution + failure record)
# ---------------------------------------------------------------------------


def test_resolver_substitutes_sentinel_and_records_failure_when_unmapped():
    from ttd_data.uid2 import IdentityScope
    from ttd_data.uid2.resolver import resolve_uid2_identifiers_in_place

    items = [_advertiser_item(email="optout@example.com")]
    client = _make_identity_map_client(
        unmapped={"optout@example.com": _unmapped("optout")}
    )

    resolutions, failures = resolve_uid2_identifiers_in_place(
        items, client, IdentityScope.UID2
    )

    assert items[0].uid2 == "*"
    assert resolutions["optout@example.com"].unmapped_reason == "optout"
    assert 0 in failures
    assert failures[0].reason == "optout"
    assert failures[0].identifier_kind == "Email"


# ---------------------------------------------------------------------------
# Resolver — transient HTTP failure path
# ---------------------------------------------------------------------------


def test_resolver_marks_chunk_failed_on_retry_exhaustion(monkeypatch):
    """When `generate_identity_map` keeps raising a retryable HTTP error,
    the resolver marks every raw id in the chunk as failed with the HTTP
    reason rather than aborting the request."""
    from ttd_data.uid2 import IdentityScope
    from ttd_data.uid2.resolver import resolve_uid2_identifiers_in_place

    # Skip the real backoff sleeps so the test runs instantly.
    monkeypatch.setattr("ttd_data.uid2.resolver.time.sleep", lambda _s: None)

    items = [_advertiser_item(email="alice@example.com")]
    client = _make_identity_map_client()
    client.generate_identity_map.side_effect = HTTPError(
        url="http://uid2", code=503, msg="Service Unavailable", hdrs=None, fp=None  # type: ignore[arg-type]
    )

    resolutions, failures = resolve_uid2_identifiers_in_place(
        items, client, IdentityScope.UID2
    )

    assert items[0].uid2 == "*"
    reason = resolutions["alice@example.com"].unmapped_reason
    assert reason is not None and "503" in reason
    assert failures[0].reason.startswith("HTTP 503")


# ---------------------------------------------------------------------------
# Resolver — catastrophic failure path
# ---------------------------------------------------------------------------


def test_resolver_raises_service_error_on_non_retryable_http():
    from ttd_data.uid2 import IdentityScope, UID2ServiceError
    from ttd_data.uid2.resolver import resolve_uid2_identifiers_in_place

    items = [_advertiser_item(email="alice@example.com")]
    client = _make_identity_map_client()
    client.generate_identity_map.side_effect = HTTPError(
        url="http://uid2", code=401, msg="Unauthorized", hdrs=None, fp=None  # type: ignore[arg-type]
    )

    with pytest.raises(UID2ServiceError, match="401"):
        resolve_uid2_identifiers_in_place(items, client, IdentityScope.UID2)


def test_resolver_raises_service_error_on_unexpected_exception():
    from ttd_data.uid2 import IdentityScope, UID2ServiceError
    from ttd_data.uid2.resolver import resolve_uid2_identifiers_in_place

    items = [_advertiser_item(email="alice@example.com")]
    client = _make_identity_map_client()
    client.generate_identity_map.side_effect = RuntimeError("kaboom")

    with pytest.raises(UID2ServiceError, match="kaboom"):
        resolve_uid2_identifiers_in_place(items, client, IdentityScope.UID2)


# ---------------------------------------------------------------------------
# DataClient — pass-through when no `uid2_config`
# ---------------------------------------------------------------------------


def test_data_client_without_uid2_config_skips_resolution(monkeypatch):
    """`DataClient()` with no `uid2_config` must not call the UID2 SDK.
    We assert by patching the resolver and confirming it was never invoked."""
    from ttd_data import DataClient
    from ttd_data.models.ingestadvertiserdataop import (
        IngestAdvertiserDataResponse as _BaseResponse,
    )

    resolver_called = MagicMock()
    monkeypatch.setattr(
        "ttd_data.client.resolve_uid2_identifiers_in_place", resolver_called
    )

    base = MagicMock()
    base.advertiser.ingest_advertiser_data.return_value = _BaseResponse.model_construct()
    client = DataClient(data_client=base)
    items = [object()]  # opaque — pass-through never inspects items
    client.advertiser.ingest_advertiser_data(items=items)

    resolver_called.assert_not_called()
    base.advertiser.ingest_advertiser_data.assert_called_once()


# ---------------------------------------------------------------------------
# PII does not leak to the outbound request body
# ---------------------------------------------------------------------------


_PII_WIRE_KEYS = {"Email", "Phone", "HashedEmail", "HashedPhone"}


def _pii_items_and_values():
    """One advertiser item per raw-PII kind, plus the raw values to grep for."""
    from ttd_data.models import AdvertiserData
    from ttd_data.uid2 import AdvertiserDataItem

    raw_values = {
        "email": "alice@example.com",
        "phone": "+15551234567",
        "hashed_email": "hashed-email-value-not-an-actual-hash",
        "hashed_phone": "hashed-phone-value-not-an-actual-hash",
    }
    items = [
        AdvertiserDataItem(data=[AdvertiserData(name="seg")], **{kind: val})
        for kind, val in raw_values.items()
    ]
    return items, set(raw_values.values())


def _wire_form(item):
    """Wire body the SDK would serialize for this item (dict + JSON)."""
    return item.model_dump(by_alias=True), item.model_dump_json(by_alias=True)


def test_top_level_pii_marks_failure_without_uid2_config():
    """When uid2_config is None and an item carries a top-level raw PII
    identifier, the SDK must substitute the "*" sentinel into the uid2 field,
    UNSET the raw field, and record a failed_mapping — but still send the
    request to the API. Mirrors the existing opt-out/unmapped path: partial
    failure semantics instead of a whole-request rejection."""
    from ttd_data.models import AdvertiserData
    from ttd_data.uid2 import AdvertiserDataItem
    from ttd_data.uid2.resolver import mark_raw_pii_failures_without_uid2

    raw_kinds = ["email", "phone", "hashed_email", "hashed_phone"]
    for kind in raw_kinds:
        item = AdvertiserDataItem(data=[AdvertiserData(name="seg")], **{kind: "raw_pii_value"})
        _resolutions, failed = mark_raw_pii_failures_without_uid2([item])

        # Sentinel substituted into uid2 field
        assert item.uid2 == "*", f"expected uid2='*' after marking, got {item.uid2!r}"
        # Raw field UNSET so it cannot reach the wire
        assert not getattr(item, kind), f"expected {kind} cleared, got {getattr(item, kind)!r}"
        # Failure recorded for this item
        assert failed.keys() == {0}, f"expected failure keyed by index 0, got {failed.keys()}"
        assert "uid2_config" in failed[0].reason.lower()


def test_user_id_array_pii_marks_failure_without_uid2_config():
    """`user_id_array` entries with raw-PII type codes (-1..-4) must be rewritten
    in place to [UserIdType.UID2, '*'] and a per-item failure recorded — same
    sentinel + failed_mapping pattern as the resolver uses for unmapped ids."""
    from ttd_data.models import OfflineConversionDataItem
    from ttd_data.uid2 import UserIdType
    from ttd_data.uid2.resolver import mark_raw_pii_failures_without_uid2

    item = OfflineConversionDataItem(
        tracking_tag_id="tag",
        timestamp_utc=datetime(2025, 1, 1, tzinfo=timezone.utc),
        user_id_array=[
            [UserIdType.TDID,  "df2df528-e032-4851-b7c6-99287c7d6bcd"],  # untouched
            [UserIdType.EMAIL, "alice@example.com"],                     # rewritten
        ],
    )
    _resolutions, failed = mark_raw_pii_failures_without_uid2([item])

    # TDID entry untouched (first-valid-wins fallback still works)
    assert item.user_id_array[0] == [UserIdType.TDID, "df2df528-e032-4851-b7c6-99287c7d6bcd"]
    # Email entry rewritten to [UID2, "*"]
    assert item.user_id_array[1] == [UserIdType.UID2.value, "*"]
    # Failure recorded for this item
    assert failed.keys() == {0}
    assert "uid2_config" in failed[0].reason.lower()


def test_request_still_goes_out_with_partial_failure_when_no_uid2_config():
    """End-to-end (mocked base SDK): one PII item + one pre-resolved item.
    The base SDK must be called with BOTH items (the PII one carrying the
    sentinel), and the proxy returns failed_mappings keyed only by the PII
    item's index."""
    from ttd_data import DataClient
    from ttd_data.models import AdvertiserData
    from ttd_data.uid2 import AdvertiserDataItem
    from ttd_data.models.ingestadvertiserdataop import (
        IngestAdvertiserDataResponse as _BaseResponse,
    )

    items = [
        AdvertiserDataItem(data=[AdvertiserData(name="seg")], email="alice@example.com"),
        AdvertiserDataItem(data=[AdvertiserData(name="seg")], tdid="df2df528-e032-4851-b7c6-99287c7d6bcd"),
    ]

    base = MagicMock()
    base.advertiser.ingest_advertiser_data.return_value = _BaseResponse.model_construct()
    client = DataClient(data_client=base)
    client.advertiser.ingest_advertiser_data(items=items)

    # Both items forwarded — partial failure, not whole-request rejection.
    base.advertiser.ingest_advertiser_data.assert_called_once()
    forwarded_items = base.advertiser.ingest_advertiser_data.call_args.kwargs["items"]
    assert len(forwarded_items) == 2

    # PII item now carries the sentinel and no raw email anywhere on the wire.
    forwarded_dict = forwarded_items[0].model_dump(by_alias=True)
    forwarded_json = forwarded_items[0].model_dump_json(by_alias=True)
    assert forwarded_dict.get("UID2") == "*"
    assert "alice@example.com" not in forwarded_json
    assert "Email" not in forwarded_dict
    # Pre-resolved item untouched.
    assert forwarded_items[1].model_dump(by_alias=True).get("TDID") == "df2df528-e032-4851-b7c6-99287c7d6bcd"


def test_non_pii_items_pass_through_without_uid2_config():
    """Regression check on the strict PII guard: items that don't carry raw
    PII (pre-resolved TDID/UID2/RampID etc.) must still flow through with
    no UID2Config, the same as before the guard was introduced."""
    from ttd_data import DataClient
    from ttd_data.models import OfflineConversionDataItem
    from ttd_data.models.ingestofflineconversiondataop import (
        IngestOfflineConversionDataResponse as _BaseResponse,
    )
    from ttd_data.uid2 import UserIdType

    item = OfflineConversionDataItem(
        tracking_tag_id="tag",
        timestamp_utc=datetime(2025, 1, 1, tzinfo=timezone.utc),
        user_id_array=[
            [UserIdType.TDID, "df2df528-e032-4851-b7c6-99287c7d6bcd"],
            [UserIdType.UID2, "48MjlfIUZpOKNAm9nod7/jCLAXUYsnE1tpVHQSDS0uo="],
        ],
    )
    base = MagicMock()
    base.offline_conversion.ingest_offline_conversion_data.return_value = (
        _BaseResponse.model_construct()
    )
    client = DataClient(data_client=base)
    client.offline_conversion.ingest_offline_conversion_data(items=[item])
    base.offline_conversion.ingest_offline_conversion_data.assert_called_once()


def test_no_pii_on_wire_with_uid2_config(monkeypatch):
    """With a UID2Config, the resolver substitutes raw identifiers with the
    resolved UID2 and clears the raw fields. The wire body must carry UID2
    values, not the original email/phone/hashed_email/hashed_phone."""
    from ttd_data import DataClient, IdentityScope, UID2Config
    from ttd_data.models.ingestadvertiserdataop import (
        IngestAdvertiserDataResponse as _BaseResponse,
    )

    items, pii_values = _pii_items_and_values()
    pii_to_uid2 = {
        raw: f"opaque-uid-{i}" for i, raw in enumerate(sorted(pii_values))
    }
    expected_uids = set(pii_to_uid2.values())
    fake_identity_map = _make_identity_map_client(
        mapped={raw: _mapped(uid) for raw, uid in pii_to_uid2.items()}
    )
    monkeypatch.setattr(
        "ttd_data.client.IdentityMapV3Client", lambda *_a, **_k: fake_identity_map
    )

    base = MagicMock()
    base.advertiser.ingest_advertiser_data.return_value = _BaseResponse.model_construct()
    uid2_config = UID2Config(
        base_url="https://uid2.example.com",
        api_key="key",
        client_secret="secret",
        identity_scope=IdentityScope.UID2,
    )
    client = DataClient(uid2_config=uid2_config, data_client=base)
    client.advertiser.ingest_advertiser_data(items=items)

    forwarded_items = base.advertiser.ingest_advertiser_data.call_args.kwargs["items"]
    assert len(forwarded_items) == len(items)
    seen_uids = set()
    for item in forwarded_items:
        wire_dict, wire_json = _wire_form(item)
        leaked_keys = _PII_WIRE_KEYS & set(wire_dict.keys())
        assert not leaked_keys, f"PII key on wire: {leaked_keys} in {wire_dict}"
        leaked_values = {v for v in pii_values if v in wire_json}
        assert not leaked_values, f"PII value on wire: {leaked_values} in {wire_json}"
        uid2 = wire_dict.get("UID2")
        if uid2:
            seen_uids.add(uid2)
    assert seen_uids == expected_uids, f"expected {expected_uids}, got {seen_uids}"
