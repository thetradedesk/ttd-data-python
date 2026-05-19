"""Unit tests for the UID2 wrapper layer (`ttd_data.DataClient`, the resolver,
and the at-most-one-identifier validator). No network; the UID2 SDK client
is mocked."""

from __future__ import annotations

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
    from ttd_data import DataClient, IdentityScope, UID2Config  # noqa: F401
    from ttd_data.uid2 import (  # noqa: F401
        AdvertiserDataItem,
        OfflineConversionDataItem,
        PartnerDsrDataItem,
        ThirdPartyDataItem,
        UID2ServiceError,
    )


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


def test_no_pii_on_wire_without_uid2_config():
    """Wrapper items carrying raw PII (email/phone/hashed_email/hashed_phone)
    must have those fields stripped before the request leaves the SDK, even
    when no UID2Config is supplied. The wrapper→base conversion in
    `_prepare_items_for_request` drops them because the base item type does
    not declare those fields."""
    from ttd_data import DataClient
    from ttd_data.models.ingestadvertiserdataop import (
        IngestAdvertiserDataResponse as _BaseResponse,
    )

    items, pii_values = _pii_items_and_values()

    base = MagicMock()
    base.advertiser.ingest_advertiser_data.return_value = _BaseResponse.model_construct()
    client = DataClient(data_client=base)
    client.advertiser.ingest_advertiser_data(items=items)

    forwarded_items = base.advertiser.ingest_advertiser_data.call_args.kwargs["items"]
    assert len(forwarded_items) == len(items)
    for item in forwarded_items:
        wire_dict, wire_json = _wire_form(item)
        leaked_keys = _PII_WIRE_KEYS & set(wire_dict.keys())
        assert not leaked_keys, f"PII key on wire: {leaked_keys} in {wire_dict}"
        leaked_values = {v for v in pii_values if v in wire_json}
        assert not leaked_values, f"PII value on wire: {leaked_values} in {wire_json}"


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
