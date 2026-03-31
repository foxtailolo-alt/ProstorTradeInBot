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


class DamProdamApiClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        *,
        base_url: str = "https://damprodam.ru/py/",
    ) -> None:
        self._external_client = http_client
        self._base_url = base_url

    async def fetch_category_params(self, category: SupportedCategory) -> Any:
        endpoint, payload = _PARAMS_ENDPOINTS[category]
        response = await self._request("POST", endpoint, json=payload)
        return response.json()

    async def aclose(self) -> None:
        if self._external_client is None:
            return
        await self._external_client.aclose()

    async def _request(self, method: str, path: str, json: Mapping[str, Any]) -> httpx.Response:
        if self._external_client is not None:
            response = await self._external_client.request(method, path, json=json)
            response.raise_for_status()
            return response

        async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as client:
            response = await client.request(method, path, json=json)
            response.raise_for_status()
            return response