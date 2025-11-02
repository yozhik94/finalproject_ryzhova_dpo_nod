"""
Иерархия классов для валют и реестр для их получения.
"""
from abc import ABC, abstractmethod
from typing import Dict

from .exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактный базовый класс для всех валют."""
    def __init__(self, name: str, code: str):
        if not name or not isinstance(name, str):
            raise ValueError("Имя валюты не может быть пустым.")
        if not (isinstance(code, str) and 2 <= len(code) <= 5 and code.isupper()):
            raise ValueError("Код валюты должен быть строкой 2-5 заглавных букв.")
        
        self.name = name
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает строковое представление для UI/логов."""
        pass

class FiatCurrency(Currency):
    """Представляет фиатную валюту."""
    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        return (
            f"[FIAT] {self.code} — {self.name} "
            f"(Issuing: {self.issuing_country})"
        )

class CryptoCurrency(Currency):
    """Представляет криптовалюту."""
    def __init__(self, name: str, code: str, algorithm: str, market_cap: float):
        super().__init__(name, code)
        self.algorithm = algorithm
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        # Форматируем market_cap для читаемости
        if self.market_cap >= 1e12:
            mc_str = f"{self.market_cap / 1e12:.2f}T"
        elif self.market_cap >= 1e9:
            mc_str = f"{self.market_cap / 1e9:.2f}B"
        else:
            mc_str = f"{self.market_cap:.2f}"
            
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: ${mc_str})"
        )

# --- Реестр Валют ---
_CURRENCY_REGISTRY: Dict[str, Currency] = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.2e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 3.6e11),
}

def get_currency(code: str) -> Currency:
    """
    Фабричная функция для получения экземпляра валюты по ее коду.
    
    Raises:
        CurrencyNotFoundError: Если код валюты не найден в реестре.
    """
    currency = _CURRENCY_REGISTRY.get(code.upper())
    if not currency:
        raise CurrencyNotFoundError(code)
    return currency

def get_all_currency_codes() -> list[str]:
    """Возвращает список всех поддерживаемых кодов валют."""
    return list(_CURRENCY_REGISTRY.keys())

