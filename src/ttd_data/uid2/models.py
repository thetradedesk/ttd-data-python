from __future__ import annotations

import pydantic
from pydantic import model_serializer, model_validator
from typing import Any, Dict, Iterable
from typing_extensions import Annotated, NotRequired

from ttd_data.types import Nullable, OptionalNullable, UNSET, UNSET_SENTINEL
from ttd_data.models.baseadvertiserdataitem import (
    BaseAdvertiserDataItem,
    BaseAdvertiserDataItemTypedDict,
)
from ttd_data.models.basethirdpartydataitem import (
    BaseThirdPartyDataItem,
    BaseThirdPartyDataItemTypedDict,
)
from ttd_data.models.basepartnerdsrdataitem import (
    BasePartnerDsrDataItem,
    BasePartnerDsrDataItemTypedDict,
)
from ttd_data.models.baseofflineconversiondataitem import (
    BaseOfflineConversionDataItem,
    BaseOfflineConversionDataItemTypedDict,
)
from ttd_data.models.ingestofflineconversiondataop import (
    IngestOfflineConversionDataResponse as _BaseIngestOfflineConversionDataResponse,
)
from ttd_data.models.ingestadvertiserdataop import (
    IngestAdvertiserDataResponse as _BaseIngestAdvertiserDataResponse,
)
from ttd_data.models.ingestthirdpartydataop import (
    IngestThirdPartyDataResponse as _BaseIngestThirdPartyDataResponse,
)
from ttd_data.models.datasubjectrequestadvertiserdataop import (
    DataSubjectRequestAdvertiserDataResponse as _BaseDataSubjectRequestAdvertiserDataResponse,
)
from ttd_data.models.datasubjectrequestmerchantdataop import (
    DataSubjectRequestMerchantDataResponse as _BaseDataSubjectRequestMerchantDataResponse,
)
from ttd_data.models.datasubjectrequestthirdpartydataop import (
    DataSubjectRequestThirdPartyDataResponse as _BaseDataSubjectRequestThirdPartyDataResponse,
)

from .resolver import UID2Resolution


_UID2_RAW_ALIASES = ("Email", "Phone", "HashedEmail", "HashedPhone")


# Identifier fields that all resolve into the UID2/EUID space. An item must
# carry at most ONE of these.
_UID2_FAMILY_FIELDS: tuple[tuple[str, str], ...] = (
    ("email", "Email"),
    ("hashed_email", "HashedEmail"),
    ("phone", "Phone"),
    ("hashed_phone", "HashedPhone"),
    ("uid2", "UID2"),
    ("uid2_token", "UID2Token"),
    ("euid", "EUID"),
    ("euid_token", "EUIDToken"),
)


def _validate_at_most_one_uid2_identifier(self: Any) -> Any:
    """`model_validator(mode='after')` hook: ensures the item carries at most
    one UID2-family identifier. Caller gets immediate feedback at object
    construction.
    """
    present: list[str] = []
    for py_attr, json_key in _UID2_FAMILY_FIELDS:
        # Count the field as present only if it has a non-empty value;
        # UNSET and empty strings both count as "not set".
        if getattr(self, py_attr, None):
            present.append(json_key)
    if len(present) > 1:
        raise ValueError(
            f"At most one UID2-family identifier may be set per item; "
            f"got {len(present)} ({', '.join(present)}). "
            f"Use exactly one of "
            f"{{Email, HashedEmail, Phone, HashedPhone, UID2, UID2Token, EUID, EUIDToken}}."
        )
    return self


def _build_serialize_model(extra_optional_fields: Iterable[str]):
    """Build a `model_serializer(mode='wrap')` that mirrors the speakeasy
    UNSET/Nullable filtering and additionally surfaces the UID2 extension
    fields (Email / Phone / HashedEmail / HashedPhone)."""
    extras_plus_existing = set(extra_optional_fields) | set(_UID2_RAW_ALIASES)

    @model_serializer(mode="wrap")
    def serialize_model(self, handler):
        serialized = handler(self)
        m = {}
        for n, f in type(self).model_fields.items():
            k = f.alias or n
            val = serialized.get(k, serialized.get(n))
            is_nullable_and_explicitly_set = (
                k in extras_plus_existing
                and (self.__pydantic_fields_set__.intersection({n}))  # pylint: disable=no-member
            )
            if val != UNSET_SENTINEL:
                if (
                    val is not None
                    or k not in extras_plus_existing
                    or is_nullable_and_explicitly_set
                ):
                    m[k] = val
        return m

    return serialize_model


# ---------------------------------------------------------------------------
# Item wrappers — extend each speakeasy item type with raw / hashed email +
# phone identifiers. `resolve_uid2_identifiers_in_place` resolves them to a UID2 before
# the request leaves the SDK.
# ---------------------------------------------------------------------------


class AdvertiserDataItemTypedDict(BaseAdvertiserDataItemTypedDict, total=False):
    email: NotRequired[Nullable[str]]
    phone: NotRequired[Nullable[str]]
    hashed_email: NotRequired[Nullable[str]]
    hashed_phone: NotRequired[Nullable[str]]


class AdvertiserDataItem(BaseAdvertiserDataItem):
    """`BaseAdvertiserDataItem` extended with raw / hashed email + phone."""

    email: Annotated[OptionalNullable[str], pydantic.Field(alias="Email")] = UNSET
    phone: Annotated[OptionalNullable[str], pydantic.Field(alias="Phone")] = UNSET
    hashed_email: Annotated[
        OptionalNullable[str], pydantic.Field(alias="HashedEmail")
    ] = UNSET
    hashed_phone: Annotated[
        OptionalNullable[str], pydantic.Field(alias="HashedPhone")
    ] = UNSET

    _validate_uid2_family = model_validator(mode="after")(_validate_at_most_one_uid2_identifier)

    serialize_model = _build_serialize_model({
        "TDID", "DAID", "UID2", "UID2Token", "RampID", "CoreID", "EUID",
        "EUIDToken", "ID5", "NetID", "FirstID", "MerkuryID", "IqviaPPID",
        "CookieMappingPartnerId",
    })


class ThirdPartyDataItemTypedDict(BaseThirdPartyDataItemTypedDict, total=False):
    email: NotRequired[Nullable[str]]
    phone: NotRequired[Nullable[str]]
    hashed_email: NotRequired[Nullable[str]]
    hashed_phone: NotRequired[Nullable[str]]


class ThirdPartyDataItem(BaseThirdPartyDataItem):
    """`BaseThirdPartyDataItem` extended with raw / hashed email + phone."""

    email: Annotated[OptionalNullable[str], pydantic.Field(alias="Email")] = UNSET
    phone: Annotated[OptionalNullable[str], pydantic.Field(alias="Phone")] = UNSET
    hashed_email: Annotated[
        OptionalNullable[str], pydantic.Field(alias="HashedEmail")
    ] = UNSET
    hashed_phone: Annotated[
        OptionalNullable[str], pydantic.Field(alias="HashedPhone")
    ] = UNSET

    _validate_uid2_family = model_validator(mode="after")(_validate_at_most_one_uid2_identifier)

    serialize_model = _build_serialize_model({
        "DataProviderUserId", "TDID", "DAID", "UID2", "UID2Token", "RampID",
        "CoreID", "EUID", "EUIDToken", "ID5", "NetID", "FirstID", "MerkuryID",
        "IqviaPPID", "CookieMappingPartnerId",
    })


class PartnerDsrDataItemTypedDict(BasePartnerDsrDataItemTypedDict, total=False):
    email: NotRequired[Nullable[str]]
    phone: NotRequired[Nullable[str]]
    hashed_email: NotRequired[Nullable[str]]
    hashed_phone: NotRequired[Nullable[str]]


class PartnerDsrDataItem(BasePartnerDsrDataItem):
    """`BasePartnerDsrDataItem` extended with raw / hashed email + phone."""

    email: Annotated[OptionalNullable[str], pydantic.Field(alias="Email")] = UNSET
    phone: Annotated[OptionalNullable[str], pydantic.Field(alias="Phone")] = UNSET
    hashed_email: Annotated[
        OptionalNullable[str], pydantic.Field(alias="HashedEmail")
    ] = UNSET
    hashed_phone: Annotated[
        OptionalNullable[str], pydantic.Field(alias="HashedPhone")
    ] = UNSET

    _validate_uid2_family = model_validator(mode="after")(_validate_at_most_one_uid2_identifier)

    serialize_model = _build_serialize_model({
        "TDID", "DAID", "UID2", "UID2Token", "RampID", "CoreID", "EUID",
        "EUIDToken", "ID5", "NetID", "FirstID", "MerkuryID", "IqviaPPID",
    })


class OfflineConversionDataItemTypedDict(
    BaseOfflineConversionDataItemTypedDict, total=False
):
    email: NotRequired[Nullable[str]]
    phone: NotRequired[Nullable[str]]
    hashed_email: NotRequired[Nullable[str]]
    hashed_phone: NotRequired[Nullable[str]]


class OfflineConversionDataItem(BaseOfflineConversionDataItem):
    """`BaseOfflineConversionDataItem` extended with raw / hashed email + phone."""

    email: Annotated[OptionalNullable[str], pydantic.Field(alias="Email")] = UNSET
    phone: Annotated[OptionalNullable[str], pydantic.Field(alias="Phone")] = UNSET
    hashed_email: Annotated[
        OptionalNullable[str], pydantic.Field(alias="HashedEmail")
    ] = UNSET
    hashed_phone: Annotated[
        OptionalNullable[str], pydantic.Field(alias="HashedPhone")
    ] = UNSET

    _validate_uid2_family = model_validator(mode="after")(_validate_at_most_one_uid2_identifier)

    serialize_model = _build_serialize_model({
        "TDID", "DAID", "UID2", "UID2Token", "RampID", "EUID", "EUIDToken",
        "DataProviderUserId", "UserIdArray", "CookieMappingPartnerId",
        "OrderId", "ImpressionId", "Value", "ValueCurrency", "Country",
        "Region", "Metro", "City", "MerchantId", "EventName", "LineItems",
        "PrivacySettings", "TD1", "TD2", "TD3", "TD4", "TD5", "TD6", "TD7",
        "TD8", "TD9", "TD10",
    })


# ---------------------------------------------------------------------------
# Response wrappers — each adds `identity_resolutions` (a dict keyed by raw
# identifier) on top of the speakeasy-generated response. `exclude=True`
# keeps the field out of any wire serialization.
# ---------------------------------------------------------------------------


def _empty_resolutions() -> Dict[str, Any]:
    return {}


_resolution_field: Any = pydantic.Field(default_factory=_empty_resolutions, exclude=True)


class IngestAdvertiserDataResponse(_BaseIngestAdvertiserDataResponse):
    identity_resolutions: Annotated[Dict[str, UID2Resolution], _resolution_field]


class IngestThirdPartyDataResponse(_BaseIngestThirdPartyDataResponse):
    identity_resolutions: Annotated[Dict[str, UID2Resolution], _resolution_field]


class IngestOfflineConversionDataResponse(_BaseIngestOfflineConversionDataResponse):
    identity_resolutions: Annotated[Dict[str, UID2Resolution], _resolution_field]


class DataSubjectRequestAdvertiserDataResponse(
    _BaseDataSubjectRequestAdvertiserDataResponse
):
    identity_resolutions: Annotated[Dict[str, UID2Resolution], _resolution_field]


class DataSubjectRequestMerchantDataResponse(
    _BaseDataSubjectRequestMerchantDataResponse
):
    identity_resolutions: Annotated[Dict[str, UID2Resolution], _resolution_field]


class DataSubjectRequestThirdPartyDataResponse(
    _BaseDataSubjectRequestThirdPartyDataResponse
):
    identity_resolutions: Annotated[Dict[str, UID2Resolution], _resolution_field]


try:
    AdvertiserDataItem.model_rebuild()
    ThirdPartyDataItem.model_rebuild()
    OfflineConversionDataItem.model_rebuild()
    PartnerDsrDataItem.model_rebuild()
    IngestAdvertiserDataResponse.model_rebuild()
    IngestThirdPartyDataResponse.model_rebuild()
    IngestOfflineConversionDataResponse.model_rebuild()
    DataSubjectRequestAdvertiserDataResponse.model_rebuild()
    DataSubjectRequestMerchantDataResponse.model_rebuild()
    DataSubjectRequestThirdPartyDataResponse.model_rebuild()
except NameError:
    pass
