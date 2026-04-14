from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from src.domain.enums import SupportedCategory


_PARAMS_ENDPOINTS: dict[SupportedCategory, tuple[str, dict[str, Any]]] = {
    SupportedCategory.IPHONE: ("iphone_buyout/params", {}),
    SupportedCategory.MAC: ("macbook_buyout/params", {}),
    SupportedCategory.SAMSUNG: ("android_buyout/params", {"vendor": "samsung"}),
    SupportedCategory.IPAD: ("ipad_buyout/params", {}),
    SupportedCategory.APPLE_WATCH: ("watches_buyout/params", {}),
}

_PRICING_ENDPOINTS: dict[SupportedCategory, str] = {
    SupportedCategory.IPHONE: "iphone_buyout",
    SupportedCategory.MAC: "macbook_buyout",
    SupportedCategory.SAMSUNG: "android_buyout",
    SupportedCategory.IPAD: "ipad_buyout",
    SupportedCategory.APPLE_WATCH: "watches_buyout",
}


class DamProdamApiClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        *,
        base_url: str = "https://damprodam.ru/py/",
    ) -> None:
        self._external_client = http_client
        self._base_url = base_url

    async def fetch_category_params(
        self,
        category: SupportedCategory,
        payload: Mapping[str, Any] | None = None,
    ) -> Any:
        endpoint, default_payload = _PARAMS_ENDPOINTS[category]
        merged_payload = dict(default_payload)
        if payload:
            merged_payload.update(payload)
        response = await self._request("POST", endpoint, json=merged_payload)
        return response.json()

    async def fetch_buyout_price(
        self,
        category: SupportedCategory,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        response = await self._request(
            "POST",
            _PRICING_ENDPOINTS[category],
            data=self._stringify_form_payload(payload),
        )
        return response.json()

    async def aclose(self) -> None:
        if self._external_client is None:
            return
        await self._external_client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
    ) -> httpx.Response:
        if self._external_client is not None:
            response = await self._external_client.request(method, path, json=json, data=data)
            response.raise_for_status()
            return response

        async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as client:
            response = await client.request(method, path, json=json, data=data)
            response.raise_for_status()
            return response

    @staticmethod
    def _stringify_form_payload(payload: Mapping[str, Any]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, value in payload.items():
            if value is None:
                continue
            if isinstance(value, bool):
                normalized[key] = str(value).lower()
                continue
            normalized[key] = str(value)
        return normalized