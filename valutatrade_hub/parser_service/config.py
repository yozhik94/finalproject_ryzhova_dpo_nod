"""
Конфигурация для Parser Service.

Содержит настройки API, список поддерживаемых валют
и параметры обновления курсов.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


@dataclass
class ParserConfig:
    """Конфигурация парсера курсов валют."""

    # API URLs
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # API Keys (загружаются из переменных окружения)
    # ВАЖНО: Атрибут с МАЛЕНЬКИМИ буквами для совместимости с api_clients.py
    EXCHANGERATE_API_KEY: str = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY", "")
    )

    # Mapping криптовалют для CoinGecko API
    CRYPTO_ID_MAP: dict = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "USDT": "tether",
        }
    )

    # Фиатные валюты для ExchangeRate-API
    FIAT_CURRENCIES: list = field(
        default_factory=lambda: ["EUR", "GBP", "RUB", "CNY", "JPY", "AUD"]
    )

    # Базовая валюта для конвертации
    BASE_CURRENCY: str = "USD"

    # Пути к файлам хранилища
    DATA_DIR: Path = field(default_factory=lambda: Path("data"))

    @property
    def RATES_FILE_PATH(self) -> Path:
        return self.DATA_DIR / "rates.json"

    @property
    def HISTORY_FILE_PATH(self) -> Path:
        return self.DATA_DIR / "exchange_rates.json"

    # Параметры обновления
    UPDATE_INTERVAL_SECONDS: int = 3600  # 1 час
    REQUEST_TIMEOUT: int = 10  # секунды
    MAX_RETRIES: int = 3


