"""
API клиенты для получения курсов валют из внешних источников.
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict

import requests

from ..core.exceptions import (
    ApiRequestError,
    InvalidResponseError,
    RateLimitError,
)
from .config import ParserConfig

logger = logging.getLogger(__name__)


class BaseApiClient(ABC):
    """Абстрактный базовый класс для всех API клиентов."""

    def __init__(self, config: ParserConfig):
        self.config = config
        self.source_name = "Unknown"

    @abstractmethod
    def fetch_rates(self) -> Dict[str, Dict[str, Any]]:
        pass

    def _make_request(
        self, url: str, service_name: str, params: dict = None
    ) -> requests.Response:
        start_time = time.perf_counter()
        try:
            response = requests.get(
                url, params=params, timeout=self.config.REQUEST_TIMEOUT
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000)
            response.request.meta = {
                "request_ms": elapsed_ms,
            }
            if response.status_code == 429:
                raise RateLimitError(service_name)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            timeout = self.config.REQUEST_TIMEOUT
            raise ApiRequestError(
                service_name, message=f"Request timeout after {timeout}s"
            )
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(service_name, message=str(e))


class CoinGeckoClient(BaseApiClient):
    """Клиент для CoinGecko API."""

    def __init__(self, config: ParserConfig):
        super().__init__(config)
        self.source_name = "CoinGecko"

    def fetch_rates(self) -> Dict[str, Dict[str, Any]]:
        crypto_ids = ",".join(self.config.CRYPTO_ID_MAP.values())
        params = {
            "ids": crypto_ids,
            "vs_currencies": self.config.BASE_CURRENCY.lower(),
        }
        response = self._make_request(
            self.config.COINGECKO_URL, self.source_name, params=params
        )
        return self._parse_response(response.json(), response)

    def _parse_response(
        self, data: dict, response: requests.Response
    ) -> Dict[str, Dict[str, Any]]:
        rates = {}
        meta_base = {
            "request_ms": response.request.meta["request_ms"],
            "status_code": response.status_code,
            "etag": response.headers.get("ETag"),
        }
        try:
            for ticker, coin_id in self.config.CRYPTO_ID_MAP.items():
                if coin_id in data:
                    rate_key = f"{ticker}_{self.config.BASE_CURRENCY}"
                    rate_value = float(
                        data[coin_id][self.config.BASE_CURRENCY.lower()]
                    )
                    meta = meta_base.copy()
                    meta["raw_id"] = coin_id
                    rates[rate_key] = {"rate": rate_value, "meta": meta}
            return rates
        except (KeyError, ValueError, TypeError) as e:
            raise InvalidResponseError(
                self.source_name, f"Invalid response: {e}"
            )


class ExchangeRateApiClient(BaseApiClient):
    """Клиент для ExchangeRate-API."""

    def __init__(self, config: ParserConfig):
        super().__init__(config)
        self.source_name = "ExchangeRate-API"

    def fetch_rates(self) -> Dict[str, Dict[str, Any]]:
        if not self.config.EXCHANGERATE_API_KEY:
            raise ApiRequestError(self.source_name, message="API key not set")

        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{self.config.EXCHANGERATE_API_KEY}/"
            f"latest/{self.config.BASE_CURRENCY}"
        )
        response = self._make_request(url, self.source_name)
        return self._parse_response(response.json(), response)

    def _parse_response(
        self, data: dict, response: requests.Response
    ) -> Dict[str, Dict[str, Any]]:
        try:
            if data.get("result") != "success":
                raise InvalidResponseError(
                    self.source_name, f"API error: {data.get('error-type')}"
                )

            meta_base = {
                "request_ms": response.request.meta["request_ms"],
                "status_code": response.status_code,
                "etag": response.headers.get("ETag"),
            }
            rates = {}

            # ИСПРАВЛЕНО: ExchangeRate-API v6 использует
            # "conversion_rates", не "rates"
            conversion_rates = data.get("conversion_rates", {})
            base_code = data.get("base_code", self.config.BASE_CURRENCY)

            for currency in self.config.FIAT_CURRENCIES:
                if currency in conversion_rates:
                    rate_key = f"{currency}_{base_code}"
                    rate_value = float(conversion_rates[currency])
                    meta = meta_base.copy()
                    meta["raw_id"] = currency
                    rates[rate_key] = {"rate": rate_value, "meta": meta}
            return rates
        except (KeyError, ValueError, TypeError) as e:
            raise InvalidResponseError(
                self.source_name, f"Invalid response: {e}"
            )





