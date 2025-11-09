"""
Координатор обновления курсов валют (Rates Updater).
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..core.exceptions import ApiRequestError
from .api_clients import BaseApiClient, CoinGeckoClient, ExchangeRateApiClient
from .config import ParserConfig
from .storage import RatesStorage

logger = logging.getLogger(__name__)


class RatesUpdater:
    """Координатор обновления курсов валют."""

    def __init__(self, config: Optional[ParserConfig] = None):
        self.config = config or ParserConfig()
        self.storage = RatesStorage(self.config)
        self.clients: Dict[str, BaseApiClient] = {
            "coingecko": CoinGeckoClient(self.config),
            "exchangerate": ExchangeRateApiClient(self.config),
        }
        logger.info(
            "RatesUpdater initialized with clients: %s",
            ", ".join(self.clients.keys()),
        )

    def update_rates(self, source: Optional[str] = None) -> Dict[str, Any]:
        """Обновляет курсы валют и сохраняет их в правильном формате."""
        clients_to_run = self._get_clients_to_run(source)
        logger.info(f"Starting rates update from: {list(clients_to_run.keys())}")

        timestamp = datetime.now(timezone.utc)
        all_rates_data: Dict[str, Dict[str, Any]] = {}
        sources_info: Dict[str, Dict] = {}
        errors: List[str] = []

        for name, client in clients_to_run.items():
            try:
                rates_data = client.fetch_rates()
                if rates_data:
                    self.storage.save_to_history(rates_data, name, timestamp)

                all_rates_data.update(rates_data)
                sources_info[name] = {"success": True, "rates": len(rates_data)}
            except ApiRequestError as e:
                error_msg = f"Failed to fetch from {name.capitalize()}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                sources_info[name] = {
                    "success": False,
                    "error": str(e),
                    "rates": 0,
                }

        # Сохраняем курсы через storage, который теперь знает правильный формат
        if all_rates_data:
            self.storage.update_rates_cache(
                rates_data=all_rates_data,
                source="ParserService",
                timestamp=timestamp
            )

        return self._build_report(
            len(all_rates_data), timestamp, sources_info, errors
        )

    def _get_clients_to_run(
        self, source: Optional[str]
    ) -> Dict[str, BaseApiClient]:
        if source:
            client = self.clients.get(source.lower())
            if not client:
                raise ValueError(f"Unknown source: {source}")
            return {source.lower(): client}
        return self.clients

    def _build_report(
        self,
        total_rates: int,
        timestamp: datetime,
        sources: Dict,
        errors: List[str],
    ) -> Dict[str, Any]:
        """Собирает итоговый отчет об обновлении."""
        return {
            "success": len(errors) == 0,
            "timestamp": timestamp.isoformat() + "Z",
            "total_rates": total_rates,
            "sources": sources,
        }

    def get_current_rates(self) -> Dict:
        """Получает текущие курсы из кеша."""
        return self.storage.get_rates_cache()






