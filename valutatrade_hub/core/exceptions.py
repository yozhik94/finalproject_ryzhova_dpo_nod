"""
Пользовательские исключения для приложения Currency Wallet.
"""

class BaseWalletException(Exception):
    """Базовое исключение для всех ошибок приложения."""
    pass

class InsufficientFundsError(BaseWalletException):
    """Выбрасывается при недостатке средств на кошельке."""
    def __init__(self, available: float, required: float, code: str):
        self.available = available
        self.required = required
        self.code = code
        super().__init__(
            f"Недостаточно средств: доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )

class CurrencyNotFoundError(BaseWalletException):
    """Выбрасывается, если валюта не найдена в реестре."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")

class ApiRequestError(BaseWalletException):
    """Выбрасывается при сбое внешнего API курсов."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
