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


# --- Исключения для Parser Service ---

class ApiRequestError(BaseWalletException):
    """
    Исключение для ошибок при запросе к внешним API.
    Наследуется от BaseWalletException для единой иерархии.
    """
    def __init__(
        self,
        service_name: str,
        status_code: int = None,
        message: str = "API request failed"
    ):
        self.service_name = service_name
        self.status_code = status_code
        self.message = f"[{service_name}] {message}"
        if status_code:
            self.message += f" (Status: {status_code})"
        super().__init__(self.message)


class RateLimitError(ApiRequestError):
    """Исключение при превышении лимита запросов к API."""
    def __init__(self, service_name: str):
        super().__init__(
            service_name,
            status_code=429,
            message="Rate limit exceeded"
        )


class InvalidResponseError(ApiRequestError):
    """Исключение при получении некорректного ответа от API."""
    def __init__(self, service_name: str, message: str = "Invalid response format"):
        super().__init__(service_name, message=message)


