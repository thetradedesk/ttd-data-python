"""Resolve raw Email / Phone / HashedEmail / HashedPhone on ingest items to
a UID2 (or EUID) via the UID2 identity-map SDK, mutating each item in place.

Per-item mapping failures substitute a "*" sentinel and are recorded for
the caller to merge into the response's `failed_lines`. Catastrophic SDK
errors raise `UID2ServiceError`. Runs before speakeasy serialization so
the subclass-only raw identifier fields are still readable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Union
from urllib.error import HTTPError

from uid2_client import IdentityMapV3Input, UnmappedIdentity  # type: ignore[import-not-found,import-untyped]

from ttd_data.types import UNSET, UNSET_SENTINEL
from ttd_data.models.baseadvertiserdataitem import BaseAdvertiserDataItem
from ttd_data.models.basethirdpartydataitem import BaseThirdPartyDataItem
from ttd_data.models.basepartnerdsrdataitem import BasePartnerDsrDataItem
from ttd_data.models.baseofflineconversiondataitem import (
    BaseOfflineConversionDataItem,
)

from .config import IdentityScope
from ttd_data.errors import UID2ServiceError


# Sentinel UID2/EUID written for items whose identifier could not be mapped.
# The Trade Desk Data APIs respond with an "invalid UID2" error for "*",
# preserving the appropriate item number in the response.
_UID2_SENTINEL = "*"

# UID2 SDK retry policy.
_RETRYABLE_HTTP_STATUS_CODES = frozenset({408, 429, 502, 503, 504})
_MAX_RETRIES_PER_BATCH = 5
_MAX_RETRY_DURATION_SECONDS = 15
_RETRY_BACKOFF_BASE_SECONDS = 0.2

# Maximum raw ids per `IdentityMapV3Input` we send to UID2.
_UID2_BATCH_SIZE = 5000



@dataclass
class UID2Resolution:
    """Per-identifier resolution result returned by the UID2 identity-map API."""

    current_raw_uid: Optional[str] = None
    previous_raw_uid: Optional[str] = None
    refresh_from: Optional[datetime] = None
    unmapped_reason: Optional[str] = None


@dataclass
class UID2FailedMapping:
    """Recorded per-item UID2 mapping failure. Keyed by 0-indexed item index
    in the caller's input list; the proxy converts to 1-indexed `ItemNumber`
    when merging into the Trade Desk Data APIs' `failed_lines`.
    """

    item_index: int
    identifier_kind: str
    reason: str
    array_index: Optional[int] = None


# Raw identifier kinds the resolver maps, as (python attr, json/alias key).
_IDENTIFIER_KINDS: Tuple[Tuple[str, str], ...] = (
    ("hashed_email", "HashedEmail"),
    ("email",        "Email"),
    ("hashed_phone", "HashedPhone"),
    ("phone",        "Phone"),
)
_EXTRA_PY_ATTRS = tuple(p for p, _ in _IDENTIFIER_KINDS)
_EXTRA_JSON_KEYS = tuple(j for _, j in _IDENTIFIER_KINDS)


def _read_field(item: Any, py_attr: str, json_key: str) -> Any:
    """Read a field off either a pydantic model or a dict, ignoring UNSET.

    Used both for source identifier fields (Email/Phone/HashedEmail/
    HashedPhone) and for the resolved target field (UID2/EUID).
    """
    if isinstance(item, dict):
        val = item.get(py_attr, item.get(json_key))
    else:
        val = getattr(item, py_attr, None)
    if val is None or val == UNSET_SENTINEL:
        return None
    return val


# (python attr name, json/alias key) for the field where we write the
# resolved id, indexed by `IdentityScope`.
_TARGET_FIELDS: Dict[IdentityScope, Tuple[str, str]] = {
    IdentityScope.UID2: ("uid2", "UID2"),
    IdentityScope.EUID: ("euid", "EUID"),
}


class UserIdType(str, Enum):
    """Type codes for `UserIdArray` entries.

    Members subclass `str`, so they're wire-compatible with the
    `List[List[str]]` field type — pass either the enum member or the raw
    string. Unknown codes are still accepted as raw strings.
    """

    TDID = "0"
    DAID = "1"
    UID2 = "2"
    UID2_TOKEN = "3"
    EUID = "4"
    EUID_TOKEN = "5"
    RAMP_ID = "6"
    # SDK-internal placeholders — resolved to UID2/EUID before send.
    HASHED_EMAIL = "-1"
    HASHED_PHONE = "-2"
    EMAIL = "-3"
    PHONE = "-4"


_USER_ID_ARRAY_RESOLVABLE_CODES: Dict[str, str] = {
    UserIdType.HASHED_EMAIL.value: "HashedEmail",
    UserIdType.HASHED_PHONE.value: "HashedPhone",
    UserIdType.EMAIL.value: "Email",
    UserIdType.PHONE.value: "Phone",
}
_USER_ID_ARRAY_TARGET_CODE: Dict[IdentityScope, str] = {
    IdentityScope.UID2: UserIdType.UID2.value,
    IdentityScope.EUID: UserIdType.EUID.value,
}


def _read_user_id_array(item: Any) -> Optional[List[List[str]]]:
    if isinstance(item, dict):
        val = item.get("user_id_array", item.get("UserIdArray"))
    else:
        val = getattr(item, "user_id_array", None)
    if val is None or val == UNSET_SENTINEL:
        return None
    return val


def _set_target(item: Any, value: str, py_attr: str, json_key: str) -> None:
    if isinstance(item, dict):
        # Prefer json-key form when caller built a dict with aliases.
        if json_key in item or py_attr not in item:
            item[json_key] = value
        else:
            item[py_attr] = value
    else:
        setattr(item, py_attr, value)


def _clear_extras(item: Any) -> None:
    if isinstance(item, dict):
        for k in (*_EXTRA_PY_ATTRS, *_EXTRA_JSON_KEYS):
            item.pop(k, None)
    else:
        for attr in _EXTRA_PY_ATTRS:
            if hasattr(item, attr):
                setattr(item, attr, UNSET)


def _record_failure(
    failed_mappings: Dict[int, UID2FailedMapping],
    item_idx: int,
    identifier_kind: str,
    reason: str,
    array_index: Optional[int] = None,
) -> None:
    """Record the first failure per item — callers see one error per row
    even if multiple identifiers on the same item failed."""
    if item_idx in failed_mappings:
        return
    failed_mappings[item_idx] = UID2FailedMapping(
        item_index=item_idx,
        identifier_kind=identifier_kind,
        reason=reason,
        array_index=array_index,
    )


def _call_identity_map_with_retry(
    identity_map_client: Any,
    identity_map_input: Any,
) -> Tuple[Optional[Any], Optional[str]]:
    """Call `generate_identity_map` with retries on transient HTTP errors.

    Returns `(response, None)` on success, or `(None, reason)` if retries
    were exhausted on a retryable HTTP status. Raises `UID2ServiceError` for
    non-retryable HTTP errors or unexpected exceptions.
    """
    start = time.monotonic()
    last_http_error: Optional[HTTPError] = None
    for attempt in range(_MAX_RETRIES_PER_BATCH):
        try:
            return identity_map_client.generate_identity_map(identity_map_input), None
        except HTTPError as exc:
            if exc.code not in _RETRYABLE_HTTP_STATUS_CODES:
                raise UID2ServiceError(
                    f"UID2 identity-map non-retryable HTTP {exc.code} {exc.reason}"
                ) from exc
            last_http_error = exc
            if time.monotonic() - start >= _MAX_RETRY_DURATION_SECONDS:
                break
            # Exponential backoff, capped at the remaining budget.
            backoff = min(
                _RETRY_BACKOFF_BASE_SECONDS * (2 ** attempt),
                max(0.0, _MAX_RETRY_DURATION_SECONDS - (time.monotonic() - start)),
            )
            if backoff > 0:
                time.sleep(backoff)
        except UID2ServiceError:
            raise
        except Exception as exc:
            raise UID2ServiceError(
                f"UID2 identity-map unexpected error: {exc.__class__.__name__}: {exc}"
            ) from exc
    assert last_http_error is not None
    return None, f"HTTP {last_http_error.code} {last_http_error.reason}"


def _add_raw_identifiers(
    add_one: Any, raws: List[str], unmapped: Dict[str, Any]
) -> int:
    """Add raw ids to the chunk's `IdentityMapV3Input` one at a time. On
    `ValueError` from the UID2 SDK's normalization (`with_email` /
    `with_phone` reject malformed input), skip the raw id from the input
    and route it through `unmapped` so the write-back path applies the
    same "*" sentinel + Uid2Error treatment used for optout / unmapped
    identifiers. `with_hashed_email` / `with_hashed_phone` do not validate,
    so this loop is a no-op cost on the hashed-input paths.

    Returns the number of raw ids successfully added — callers use this to
    skip the network call when every raw id in a chunk was invalid.
    """
    added = 0
    for raw in raws:
        try:
            add_one(raw)
            added += 1
        except ValueError as exc:
            if raw not in unmapped:
                unmapped[raw] = UnmappedIdentity(reason=str(exc))
    return added


def _chunk_uid2_inputs(
    emails: List[str],
    hashed_emails: List[str],
    phones: List[str],
    hashed_phones: List[str],
    size: int,
) -> "Iterator[Tuple[List[str], List[str], List[str], List[str]]]":
    """Pack raw ids across kinds into chunks of at most `size` total
    raw ids. Yields one `(emails, hashed_emails, phones, hashed_phones)`
    tuple per chunk. Kinds fill in fixed order (emails → hashed_emails →
    phones → hashed_phones) so chunk contents are deterministic.

    Example with size=5000 and 6000 emails + 4000 hashed_emails:
      chunk 1 → (5000 emails, 0 hashed_emails, 0, 0)
      chunk 2 → (1000 emails, 4000 hashed_emails, 0, 0)
    """
    while emails or hashed_emails or phones or hashed_phones:
        remaining = size
        chunk_emails, emails = emails[:remaining], emails[remaining:]
        remaining -= len(chunk_emails)
        chunk_hashed_emails, hashed_emails = hashed_emails[:remaining], hashed_emails[remaining:]
        remaining -= len(chunk_hashed_emails)
        chunk_phones, phones = phones[:remaining], phones[remaining:]
        remaining -= len(chunk_phones)
        chunk_hashed_phones, hashed_phones = hashed_phones[:remaining], hashed_phones[remaining:]
        yield chunk_emails, chunk_hashed_emails, chunk_phones, chunk_hashed_phones


ItemLike = Union[
    BaseAdvertiserDataItem,
    BaseThirdPartyDataItem,
    BasePartnerDsrDataItem,
    BaseOfflineConversionDataItem,
    Dict[str, Any],
]


def resolve_uid2_identifiers_in_place(
    items: Sequence[ItemLike],
    identity_map_client: Any,
    identity_scope: IdentityScope = IdentityScope.UID2,
) -> Tuple[Dict[str, UID2Resolution], Dict[int, UID2FailedMapping]]:
    """Resolve raw ids on each item to a UID2 (or EUID, depending on
    `identity_scope`) via the UID2 identity-map SDK.

    Mutates `items` in place. On success the target field (UID2/EUID) is
    set to the resolved `current_raw_uid`; on per-item failure it is set to
    the sentinel "*" and the failure is recorded for the caller to merge
    into the Trade Desk Data APIs' `failed_lines`. Raw id fields are cleared
    either way.

    Returns `(resolutions, failed_mappings)`:
    * `resolutions` — keyed by the raw id submitted; entries for
      both mapped and unmapped ids (the latter carry `unmapped_reason`).
    * `failed_mappings` — keyed by 0-indexed input item index; one entry
      per item that had at least one raw id fail to map.
    """
    resolutions: Dict[str, UID2Resolution] = {}
    failed_mappings: Dict[int, UID2FailedMapping] = {}
    if not items:
        return resolutions, failed_mappings

    target_py_attr, target_json_key = _TARGET_FIELDS[identity_scope]
    target_user_id_array_code = _USER_ID_ARRAY_TARGET_CODE[identity_scope]

    # Bucket top-level identifiers by kind; items already carrying the target UID2/EUID are skipped.
    # Wrapper validator allows only one identifier per item, but we iterate all kinds to tolerate dict-path callers (last write wins).
    top_level_identifiers_by_kind: Dict[str, List[Tuple[int, str]]] = {
        json_key: [] for _, json_key in _IDENTIFIER_KINDS
    }
    for idx, item in enumerate(items):
        if _read_field(item, target_py_attr, target_json_key):
            continue
        for py_attr, json_key in _IDENTIFIER_KINDS:
            val = _read_field(item, py_attr, json_key)
            if val:
                top_level_identifiers_by_kind[json_key].append((idx, val))

    # Bucket UserIdArray entries by kind as (item_idx, array_idx, raw) so we can rewrite in place and pinpoint failures.
    # Items without a UserIdArray (advertiser / third-party / DSR) short-circuit via `_read_user_id_array` returning None.
    user_id_array_by_kind: Dict[str, List[Tuple[int, int, str]]] = {
        json_key: [] for _, json_key in _IDENTIFIER_KINDS
    }
    for idx, item in enumerate(items):
        arr = _read_user_id_array(item)
        if not arr:
            continue
        for arr_idx, entry in enumerate(arr):
            if not entry or len(entry) < 2:
                continue
            id_type_field = entry[0]
            type_code = (
                id_type_field.value
                if isinstance(id_type_field, Enum)
                else str(id_type_field)
            )
            resolvable_key = _USER_ID_ARRAY_RESOLVABLE_CODES.get(type_code)
            if resolvable_key is None:
                continue
            raw_id = entry[1]
            if raw_id:
                user_id_array_by_kind[resolvable_key].append((idx, arr_idx, raw_id))

    # De-dupe raw ids per kind (top-level + UserIdArray) — UID2 returns one entry per unique input.
    def _get_unique_raw_ids(json_key: str) -> List[str]:
        return list(
            {raw for _, raw in top_level_identifiers_by_kind[json_key]}
            | {raw for _, _, raw in user_id_array_by_kind[json_key]}
        )

    emails        = _get_unique_raw_ids("Email")
    hashed_emails = _get_unique_raw_ids("HashedEmail")
    phones        = _get_unique_raw_ids("Phone")
    hashed_phones = _get_unique_raw_ids("HashedPhone")

    if not (emails or hashed_emails or phones or hashed_phones):
        # No identifiers to resolve anywhere. Still clear any UNSET raw
        # fields (a no-op in practice) and return.
        for item in items:
            _clear_extras(item)
        return resolutions, failed_mappings

    # Chunk into `_UID2_BATCH_SIZE` raw ids per SDK call, each independently retried.
    # Transient-fail chunks fold into the unmapped dict (→ sentinel "*" + Uid2Error); catastrophic errors raise `UID2ServiceError` upstream.
    mapped_identities_by_raw_id: Dict[str, Any] = {}
    unmapped_identities_by_raw_id: Dict[str, Any] = {}

    for chunk_emails, chunk_hashed_emails, chunk_phones, chunk_hashed_phones in _chunk_uid2_inputs(
        emails, hashed_emails, phones, hashed_phones, _UID2_BATCH_SIZE
    ):
        chunk_input = IdentityMapV3Input()
        # Add raw ids per-item so a malformed email/phone (ValueError from `with_email`/`with_phone`) routes to `unmapped` instead of aborting the batch.
        added = 0
        added += _add_raw_identifiers(chunk_input.with_email, chunk_emails, unmapped_identities_by_raw_id)
        added += _add_raw_identifiers(chunk_input.with_hashed_email, chunk_hashed_emails, unmapped_identities_by_raw_id)
        added += _add_raw_identifiers(chunk_input.with_phone, chunk_phones, unmapped_identities_by_raw_id)
        added += _add_raw_identifiers(chunk_input.with_hashed_phone, chunk_hashed_phones, unmapped_identities_by_raw_id)

        if added == 0:
            # Every raw id in this chunk was rejected by SDK validation — skip the empty-payload call.
            continue

        response, transient_reason = _call_identity_map_with_retry(
            identity_map_client, chunk_input
        )
        if response is None:
            reason = transient_reason or "UID2 identity-map transient failure"
            transient_failure_entry = UnmappedIdentity(reason=reason)
            for raw in (*chunk_emails, *chunk_hashed_emails, *chunk_phones, *chunk_hashed_phones):
                if raw not in mapped_identities_by_raw_id and raw not in unmapped_identities_by_raw_id:
                    unmapped_identities_by_raw_id[raw] = transient_failure_entry
            continue
        mapped_identities_by_raw_id.update(response.mapped_identities)
        # Per-identifier unmapped reasons (optout, invalid, etc.) from the SDK.
        # Skip raw ids that this or a prior chunk already resolved.
        for raw, entry in response.unmapped_identities.items():
            if raw not in mapped_identities_by_raw_id:
                unmapped_identities_by_raw_id[raw] = entry

    for _, json_key in _IDENTIFIER_KINDS:
        for item_idx, raw in top_level_identifiers_by_kind[json_key]:
            resolved = mapped_identities_by_raw_id.get(raw)
            if resolved is not None:
                _set_target(
                    items[item_idx],
                    resolved.current_raw_uid,
                    target_py_attr,
                    target_json_key,
                )
                resolutions[raw] = UID2Resolution(
                    current_raw_uid=resolved.current_raw_uid,
                    previous_raw_uid=resolved.previous_raw_uid,
                    refresh_from=resolved.refresh_from,
                )
            else:
                unmapped_entry = unmapped_identities_by_raw_id.get(raw)
                reason = (
                    unmapped_entry.raw_reason if unmapped_entry else "unmapped"
                )
                _set_target(
                    items[item_idx], _UID2_SENTINEL, target_py_attr, target_json_key
                )
                resolutions[raw] = UID2Resolution(unmapped_reason=reason)
                _record_failure(failed_mappings, item_idx, json_key, reason)

        for item_idx, arr_idx, raw in user_id_array_by_kind[json_key]:
            resolved = mapped_identities_by_raw_id.get(raw)
            if resolved is not None:
                arr = _read_user_id_array(items[item_idx])
                # `_read_user_id_array` returns the live reference on pydantic
                # models, so this mutation is reflected on the item.
                arr[arr_idx] = [target_user_id_array_code, resolved.current_raw_uid]  # type: ignore[index]
                resolutions[raw] = UID2Resolution(
                    current_raw_uid=resolved.current_raw_uid,
                    previous_raw_uid=resolved.previous_raw_uid,
                    refresh_from=resolved.refresh_from,
                )
            else:
                unmapped_entry = unmapped_identities_by_raw_id.get(raw)
                reason = (
                    unmapped_entry.raw_reason if unmapped_entry else "unmapped"
                )
                arr = _read_user_id_array(items[item_idx])
                arr[arr_idx] = [target_user_id_array_code, _UID2_SENTINEL]  # type: ignore[index]
                resolutions[raw] = UID2Resolution(unmapped_reason=reason)
                _record_failure(
                    failed_mappings, item_idx, json_key, reason, array_index=arr_idx
                )

    for item in items:
        _clear_extras(item)

    return resolutions, failed_mappings
