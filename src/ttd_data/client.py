from __future__ import annotations

# DataClient wraps BaseDataClient and adds optional UID2 identity mapping.
# Supply `uid2_config` to resolve PII (email/phone) to UID2 before ingest;
# pre-resolved identifiers (TDID, UID2, DAID, etc.) work without it.
# pylint: disable=protected-access

import asyncio
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

from uid2_client import IdentityMapV3Client, IdentityMapV3Input  # type: ignore[import-not-found,import-untyped]

from ttd_data.sdk import BaseDataClient
from ttd_data.types import BaseModel, OptionalNullable
from ttd_data.utils import RetryConfig
from ttd_data.models.advertiserdataresponseerrorcode import (
    AdvertiserDataResponseErrorCode,
)
from ttd_data.models.baseadvertiserdataitem import BaseAdvertiserDataItem
from ttd_data.models.basethirdpartydataitem import BaseThirdPartyDataItem
from ttd_data.models.basepartnerdsrdataitem import BasePartnerDsrDataItem
from ttd_data.models.baseofflineconversiondataitem import (
    BaseOfflineConversionDataItem,
)
from ttd_data.models.dsrerrorcode import DsrErrorCode
from ttd_data.models.offlineconversiondataresponseerrorcode import (
    OfflineConversionDataResponseErrorCode,
)
from ttd_data.models.thirdpartydataresponseerrorcode import (
    ThirdPartyDataResponseErrorCode,
)

from .uid2.config import UID2Config
from .uid2.models import (
    AdvertiserDataItem,
    DataSubjectRequestAdvertiserDataResponse,
    DataSubjectRequestMerchantDataResponse,
    DataSubjectRequestThirdPartyDataResponse,
    IngestAdvertiserDataResponse,
    IngestOfflineConversionDataResponse,
    IngestThirdPartyDataResponse,
    OfflineConversionDataItem,
    PartnerDsrDataItem,
    ThirdPartyDataItem,
)
from .uid2.resolver import (
    UID2FailedMapping,
    UID2Resolution,
    mark_raw_pii_failures_without_uid2,
    resolve_uid2_identifiers_in_place,
)


@dataclass(frozen=True)
class ClientConfig:
    server_url: Optional[str]
    retry_config: OptionalNullable[RetryConfig]
    timeout_ms: Optional[int]
    uid2_config: Optional[UID2Config]


class DataClient:
    """DataClient for the ttd-data SDK — enables ingesting advertiser,
    third-party, offline-conversion, and deletion-opt-out data to the
    Trade Desk Data API endpoints.

    When `uid2_config` is supplied, raw email/phone ids on each item are
    resolved to UID2 (or EUID) before the request leaves; per-item mapping
    failures appear in `failed_lines` with `ErrorCode = UID2_ERROR` (the
    endpoint-specific enum member, e.g. `AdvertiserDataResponseErrorCode.UID2_ERROR`).
    """

    def __init__(
        self,
        uid2_config: Optional[UID2Config] = None,
        data_client: Optional[BaseDataClient] = None,
        **data_client_kwargs: Any,
    ) -> None:
        self.uid2_config = uid2_config
        self.data_client = data_client or BaseDataClient(**data_client_kwargs)

    @property
    def config(self) -> ClientConfig:
        """Read-only view of this client's settings, exposed immutably to
        prevent callers from mutating live client state."""
        sdk_config = self.data_client.sdk_configuration
        return ClientConfig(
            server_url=sdk_config.server_url,
            retry_config=sdk_config.retry_config,
            timeout_ms=sdk_config.timeout_ms,
            uid2_config=self.uid2_config,
        )

    # ----- UID2 identity-map wiring (internal) -----

    @cached_property
    def _identity_map_client(self) -> Any:
        """`uid2_client.IdentityMapV3Client`, built on first access. Requires `uid2_config`."""
        if self.uid2_config is None:
            raise RuntimeError(
                "UID2 identity-map access requires a UID2Config on the DataClient."
            )
        return IdentityMapV3Client(
            self.uid2_config.base_url,
            self.uid2_config.api_key,
            self.uid2_config.client_secret,
        )

    def _generate_identity_map(
        self,
        emails: Optional[Iterable[str]] = None,
        phones: Optional[Iterable[str]] = None,
        hashed_emails: Optional[Iterable[str]] = None,
        hashed_phones: Optional[Iterable[str]] = None,
    ) -> Any:
        """Call `POST /identity/map` via the UID2 SDK.

        All four identifier kinds may be supplied in the same call — UID2
        resolves each identifier independently and the response carries a
        flat map from raw identifier to resolved UID2 / unmapped reason.
        """
        emails_list = list(emails) if emails else []
        hashed_emails_list = list(hashed_emails) if hashed_emails else []
        phones_list = list(phones) if phones else []
        hashed_phones_list = list(hashed_phones) if hashed_phones else []

        if not (emails_list or hashed_emails_list or phones_list or hashed_phones_list):
            raise ValueError(
                "At least one of emails / phones / hashed_emails / hashed_phones "
                "must be provided."
            )

        identity_map_input = IdentityMapV3Input()
        if emails_list:
            identity_map_input.with_emails(emails_list)
        if hashed_emails_list:
            identity_map_input.with_hashed_emails(hashed_emails_list)
        if phones_list:
            identity_map_input.with_phones(phones_list)
        if hashed_phones_list:
            identity_map_input.with_hashed_phones(hashed_phones_list)

        return self._identity_map_client.generate_identity_map(identity_map_input)

    # ----- Internal pipeline helpers (used by sub-SDK proxies) -----

    def _prepare_items_for_request(
        self,
        items: Any,
        wrapper_cls: Type[BaseModel],
        base_cls: Type[BaseModel],
    ) -> Tuple[Any, Dict[str, UID2Resolution], Dict[int, UID2FailedMapping]]:
        """Resolve raw identifiers on `items`, then convert subclass
        instances to `base_cls`. The resolver converts emails / hashed
        emails / phones / hashed phones and sets the appropriate value
        in the UID2 / EUID fields on the `base_cls` object.

        The wrapper_cls → base_cls conversion always runs. When uid2_config
        is None, items carrying raw identifiers are sentinel-substituted and
        recorded as UID2_ERROR failures instead of going out as raw PII.
        """
        if not items:
            return items, {}, {}

        resolutions: Dict[str, UID2Resolution] = {}
        failed_mappings: Dict[int, UID2FailedMapping] = {}

        if self.uid2_config is not None:
            resolutions, failed_mappings = resolve_uid2_identifiers_in_place(
                items,
                self._identity_map_client,
                self.uid2_config.identity_scope,
            )
        else:
            resolutions, failed_mappings = mark_raw_pii_failures_without_uid2(items)

        converted: List[Any] = [
            base_cls.model_validate(it.model_dump(by_alias=True))
            if isinstance(it, wrapper_cls)
            else it
            for it in items
        ]
        return converted, resolutions, failed_mappings

    async def _prepare_items_for_request_async(
        self,
        items: Any,
        wrapper_cls: Type[BaseModel],
        base_cls: Type[BaseModel],
    ) -> Tuple[Any, Dict[str, UID2Resolution], Dict[int, UID2FailedMapping]]:
        """Async variant: runs the synchronous UID2 SDK call in a worker
        thread so the event loop stays free."""
        if not items:
            return items, {}, {}

        resolutions: Dict[str, UID2Resolution] = {}
        failed_mappings: Dict[int, UID2FailedMapping] = {}

        if self.uid2_config is not None:
            resolutions, failed_mappings = await asyncio.to_thread(
                self._resolve_items_sync, items
            )
        else:
            resolutions, failed_mappings = mark_raw_pii_failures_without_uid2(items)

        converted: List[Any] = [
            base_cls.model_validate(it.model_dump(by_alias=True))
            if isinstance(it, wrapper_cls)
            else it
            for it in items
        ]
        return converted, resolutions, failed_mappings

    def _resolve_items_sync(
        self, items: Any
    ) -> Tuple[Dict[str, UID2Resolution], Dict[int, UID2FailedMapping]]:
        """Network-bound piece, isolated for `asyncio.to_thread`. Callers must
        already have verified `self.uid2_config is not None`."""
        assert self.uid2_config is not None
        return resolve_uid2_identifiers_in_place(
            items,
            self._identity_map_client,
            self.uid2_config.identity_scope,
        )

    @staticmethod
    def _merge_failures_into_response(
        response: Any,
        server_response_attr: str,
        failed_mappings: Dict[int, UID2FailedMapping],
        error_code: Any,
    ) -> None:
        """For each `failed_lines` entry whose `ItemNumber` matches a UID2
        mapping failure, set the UID2 reason and `error_code` (the
        endpoint-specific `UID2_ERROR` enum member). Mutates `response`
        in place.
        """
        if not failed_mappings:
            return
        server_response = getattr(response, server_response_attr, None)
        if server_response is None:
            return
        lines = getattr(server_response, "failed_lines", None)
        if not lines:
            return
        for line in lines:
            item_number = getattr(line, "item_number", None)
            if item_number is None:
                continue
            try:
                idx = int(item_number) - 1
            except (TypeError, ValueError):
                continue
            failure = failed_mappings.get(idx)
            if failure is None:
                continue
            line.message = failure.reason
            line.error_code = error_code

    @staticmethod
    def _build_wrapped_response(
        response: Any,
        wrapper_cls: Type[BaseModel],
        resolutions: Dict[str, UID2Resolution],
    ) -> Any:
        """Build a `wrapper_cls` from an already-validated speakeasy response,
        attaching `identity_resolutions`.
        """
        return wrapper_cls.model_construct(
            **{f: getattr(response, f) for f in type(response).model_fields},
            identity_resolutions=resolutions,
        )

    # ----- Sub-SDK proxies -----

    @cached_property
    def advertiser(self) -> "_AdvertiserProxy":
        return _AdvertiserProxy(self)

    @cached_property
    def third_party(self) -> "_ThirdPartyProxy":
        return _ThirdPartyProxy(self)

    @cached_property
    def offline_conversion(self) -> "_OfflineConversionProxy":
        return _OfflineConversionProxy(self)

    @cached_property
    def deletion_opt_out(self) -> "_DeletionOptOutProxy":
        return _DeletionOptOutProxy(self)

    # ----- Pass-through for any sub-SDK without a UID2 wrapper -----

    def __getattr__(self, name: str) -> Any:
        return getattr(self.data_client, name)


# ---------------------------------------------------------------------------
# Sub-SDK proxies — `client.<sub>.<method>(...)` runs the resolve / convert /
# request / merge / wrap pipeline, then forwards to the speakeasy sub-SDK.
# Any method or attribute not explicitly wrapped (e.g., future endpoints
# added by speakeasy regeneration) falls through to the inner sub-SDK via
# `__getattr__`.
# ---------------------------------------------------------------------------


class _AdvertiserProxy:
    _SERVER_RESPONSE_ATTR = "advertiser_data_server_response"
    _UID2_ERROR = AdvertiserDataResponseErrorCode.UID2_ERROR

    def __init__(self, outer: DataClient) -> None:
        self._client = outer
        self._sub_sdk = outer.data_client.advertiser

    def ingest_advertiser_data(
        self, *, items: Any = None, **kwargs: Any
    ) -> IngestAdvertiserDataResponse:
        items, resolutions, failures = self._client._prepare_items_for_request(
            items, AdvertiserDataItem, BaseAdvertiserDataItem
        )
        response = self._sub_sdk.ingest_advertiser_data(items=items, **kwargs)
        self._client._merge_failures_into_response(
            response, self._SERVER_RESPONSE_ATTR, failures, self._UID2_ERROR
        )
        return self._client._build_wrapped_response(
            response, IngestAdvertiserDataResponse, resolutions
        )

    async def ingest_advertiser_data_async(
        self, *, items: Any = None, **kwargs: Any
    ) -> IngestAdvertiserDataResponse:
        items, resolutions, failures = await self._client._prepare_items_for_request_async(
            items, AdvertiserDataItem, BaseAdvertiserDataItem
        )
        response = await self._sub_sdk.ingest_advertiser_data_async(
            items=items, **kwargs
        )
        self._client._merge_failures_into_response(
            response, self._SERVER_RESPONSE_ATTR, failures, self._UID2_ERROR
        )
        return self._client._build_wrapped_response(
            response, IngestAdvertiserDataResponse, resolutions
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._sub_sdk, name)


class _ThirdPartyProxy:
    _SERVER_RESPONSE_ATTR = "third_party_data_server_response"
    _UID2_ERROR = ThirdPartyDataResponseErrorCode.UID2_ERROR

    def __init__(self, outer: DataClient) -> None:
        self._client = outer
        self._sub_sdk = outer.data_client.third_party

    def ingest_third_party_data(
        self, *, items: Any = None, **kwargs: Any
    ) -> IngestThirdPartyDataResponse:
        items, resolutions, failures = self._client._prepare_items_for_request(
            items, ThirdPartyDataItem, BaseThirdPartyDataItem
        )
        response = self._sub_sdk.ingest_third_party_data(items=items, **kwargs)
        self._client._merge_failures_into_response(
            response, self._SERVER_RESPONSE_ATTR, failures, self._UID2_ERROR
        )
        return self._client._build_wrapped_response(
            response, IngestThirdPartyDataResponse, resolutions
        )

    async def ingest_third_party_data_async(
        self, *, items: Any = None, **kwargs: Any
    ) -> IngestThirdPartyDataResponse:
        items, resolutions, failures = await self._client._prepare_items_for_request_async(
            items, ThirdPartyDataItem, BaseThirdPartyDataItem
        )
        response = await self._sub_sdk.ingest_third_party_data_async(
            items=items, **kwargs
        )
        self._client._merge_failures_into_response(
            response, self._SERVER_RESPONSE_ATTR, failures, self._UID2_ERROR
        )
        return self._client._build_wrapped_response(
            response, IngestThirdPartyDataResponse, resolutions
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._sub_sdk, name)


class _OfflineConversionProxy:
    _SERVER_RESPONSE_ATTR = "offline_conversion_data_server_response"
    _UID2_ERROR = OfflineConversionDataResponseErrorCode.UID2_ERROR

    def __init__(self, outer: DataClient) -> None:
        self._client = outer
        self._sub_sdk = outer.data_client.offline_conversion

    def ingest_offline_conversion_data(
        self, *, items: Any = None, **kwargs: Any
    ) -> IngestOfflineConversionDataResponse:
        items, resolutions, failures = self._client._prepare_items_for_request(
            items, OfflineConversionDataItem, BaseOfflineConversionDataItem
        )
        response = self._sub_sdk.ingest_offline_conversion_data(items=items, **kwargs)
        self._client._merge_failures_into_response(
            response, self._SERVER_RESPONSE_ATTR, failures, self._UID2_ERROR
        )
        return self._client._build_wrapped_response(
            response, IngestOfflineConversionDataResponse, resolutions
        )

    async def ingest_offline_conversion_data_async(
        self, *, items: Any = None, **kwargs: Any
    ) -> IngestOfflineConversionDataResponse:
        items, resolutions, failures = await self._client._prepare_items_for_request_async(
            items, OfflineConversionDataItem, BaseOfflineConversionDataItem
        )
        response = await self._sub_sdk.ingest_offline_conversion_data_async(
            items=items, **kwargs
        )
        self._client._merge_failures_into_response(
            response, self._SERVER_RESPONSE_ATTR, failures, self._UID2_ERROR
        )
        return self._client._build_wrapped_response(
            response, IngestOfflineConversionDataResponse, resolutions
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._sub_sdk, name)


class _DeletionOptOutProxy:
    _ADVERTISER_DSR_ATTR = "advertiser_dsr_response"
    _MERCHANT_DSR_ATTR = "merchant_dsr_response"
    _THIRD_PARTY_DSR_ATTR = "third_party_dsr_response"
    _UID2_ERROR = DsrErrorCode.UID2_ERROR

    def __init__(self, outer: DataClient) -> None:
        self._client = outer
        self._sub_sdk = outer.data_client.deletion_opt_out

    def data_subject_request_advertiser_data(
        self, *, items: Any = None, **kwargs: Any
    ) -> DataSubjectRequestAdvertiserDataResponse:
        items, resolutions, failures = self._client._prepare_items_for_request(
            items, PartnerDsrDataItem, BasePartnerDsrDataItem
        )
        response = self._sub_sdk.data_subject_request_advertiser_data(
            items=items, **kwargs
        )
        self._client._merge_failures_into_response(
            response, self._ADVERTISER_DSR_ATTR, failures, self._UID2_ERROR
        )
        return self._client._build_wrapped_response(
            response, DataSubjectRequestAdvertiserDataResponse, resolutions
        )

    def data_subject_request_merchant_data(
        self, *, items: Any = None, **kwargs: Any
    ) -> DataSubjectRequestMerchantDataResponse:
        items, resolutions, failures = self._client._prepare_items_for_request(
            items, PartnerDsrDataItem, BasePartnerDsrDataItem
        )
        response = self._sub_sdk.data_subject_request_merchant_data(
            items=items, **kwargs
        )
        self._client._merge_failures_into_response(
            response, self._MERCHANT_DSR_ATTR, failures, self._UID2_ERROR
        )
        return self._client._build_wrapped_response(
            response, DataSubjectRequestMerchantDataResponse, resolutions
        )

    def data_subject_request_third_party_data(
        self, *, items: Any = None, **kwargs: Any
    ) -> DataSubjectRequestThirdPartyDataResponse:
        items, resolutions, failures = self._client._prepare_items_for_request(
            items, PartnerDsrDataItem, BasePartnerDsrDataItem
        )
        response = self._sub_sdk.data_subject_request_third_party_data(
            items=items, **kwargs
        )
        self._client._merge_failures_into_response(
            response, self._THIRD_PARTY_DSR_ATTR, failures, self._UID2_ERROR
        )
        return self._client._build_wrapped_response(
            response, DataSubjectRequestThirdPartyDataResponse, resolutions
        )

    async def data_subject_request_advertiser_data_async(
        self, *, items: Any = None, **kwargs: Any
    ) -> DataSubjectRequestAdvertiserDataResponse:
        items, resolutions, failures = await self._client._prepare_items_for_request_async(
            items, PartnerDsrDataItem, BasePartnerDsrDataItem
        )
        response = await self._sub_sdk.data_subject_request_advertiser_data_async(
            items=items, **kwargs
        )
        self._client._merge_failures_into_response(
            response, self._ADVERTISER_DSR_ATTR, failures, self._UID2_ERROR
        )
        return self._client._build_wrapped_response(
            response, DataSubjectRequestAdvertiserDataResponse, resolutions
        )

    async def data_subject_request_merchant_data_async(
        self, *, items: Any = None, **kwargs: Any
    ) -> DataSubjectRequestMerchantDataResponse:
        items, resolutions, failures = await self._client._prepare_items_for_request_async(
            items, PartnerDsrDataItem, BasePartnerDsrDataItem
        )
        response = await self._sub_sdk.data_subject_request_merchant_data_async(
            items=items, **kwargs
        )
        self._client._merge_failures_into_response(
            response, self._MERCHANT_DSR_ATTR, failures, self._UID2_ERROR
        )
        return self._client._build_wrapped_response(
            response, DataSubjectRequestMerchantDataResponse, resolutions
        )

    async def data_subject_request_third_party_data_async(
        self, *, items: Any = None, **kwargs: Any
    ) -> DataSubjectRequestThirdPartyDataResponse:
        items, resolutions, failures = await self._client._prepare_items_for_request_async(
            items, PartnerDsrDataItem, BasePartnerDsrDataItem
        )
        response = await self._sub_sdk.data_subject_request_third_party_data_async(
            items=items, **kwargs
        )
        self._client._merge_failures_into_response(
            response, self._THIRD_PARTY_DSR_ATTR, failures, self._UID2_ERROR
        )
        return self._client._build_wrapped_response(
            response, DataSubjectRequestThirdPartyDataResponse, resolutions
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._sub_sdk, name)
