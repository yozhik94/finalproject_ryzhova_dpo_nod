"""
Utility helpers for ValutaTrade Hub.

Вспомогательные функции для форматирования, валидации
и работы с данными.
"""
from datetime import datetime
from typing import Optional


def format_currency(amount: float, currency_code: str) -> str:
    """
    Форматирует денежную сумму с кодом валюты.
    
    Args:
        amount: Сумма для форматирования
        currency_code: Код валюты (USD, BTC и т.д.)
        
    Returns:
        Отформатированная строка (например, "1,234.56 USD")
        
    Examples:
        >>> format_currency(1234.56, "USD")
        '1,234.56 USD'
        >>> format_currency(0.00123456, "BTC")
        '0.00123456 BTC'
    """
    code = currency_code.upper()
    
    # Для криптовалют используем больше знаков после запятой
    if code in ("BTC", "ETH", "USDT"):
        precision = 8
    else:
        precision = 2
    
    # Форматируем с разделителями тысяч
    formatted = f"{amount:,.{precision}f}"
    return f"{formatted} {code}"


def validate_amount(amount: float, min_value: float = 0.0) -> bool:
    """
    Проверяет корректность числовой суммы.
    
    Args:
        amount: Сумма для проверки
        min_value: Минимально допустимое значение (по умолчанию 0)
        
    Returns:
        True если сумма корректна, иначе False
        
    Examples:
        >>> validate_amount(100.5)
        True
        >>> validate_amount(-10)
        False
        >>> validate_amount(5, min_value=10)
        False
    """
    if not isinstance(amount, (int, float)):
        return False
    if amount < min_value:
        return False
    return True


def round_amount(amount: float, currency_code: str) -> float:
    """
    Округляет сумму в соответствии с правилами валюты.
    
    Args:
        amount: Сумма для округления
        currency_code: Код валюты
        
    Returns:
        Округленная сумма
        
    Examples:
        >>> round_amount(123.456789, "USD")
        123.46
        >>> round_amount(0.123456789, "BTC")
        0.12345679
    """
    code = currency_code.upper()
    
    # Для криптовалют используем 8 знаков
    if code in ("BTC", "ETH", "USDT"):
        return round(amount, 8)
    # Для фиатных валют - 2 знака
    return round(amount, 2)


def format_datetime(
    dt: datetime, format_str: Optional[str] = None
) -> str:
    """
    Форматирует datetime для отображения в UI.
    
    Args:
        dt: Объект datetime для форматирования
        format_str: Пользовательский формат (опционально)
        
    Returns:
        Отформатированная строка даты/времени
        
    Examples:
        >>> dt = datetime(2025, 11, 4, 15, 30, 0)
        >>> format_datetime(dt)
        '2025-11-04 15:30:00'
        >>> format_datetime(dt, "%d.%m.%Y")
        '04.11.2025'
    """
    if format_str:
        return dt.strftime(format_str)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def is_valid_currency_code(code: str) -> bool:
    """
    Быстрая проверка формата кода валюты без обращения к реестру.
    
    Args:
        code: Строка кода валюты
        
    Returns:
        True если формат корректен, иначе False
        
    Examples:
        >>> is_valid_currency_code("USD")
        True
        >>> is_valid_currency_code("BTC")
        True
        >>> is_valid_currency_code("us")
        False
        >>> is_valid_currency_code("TOOLONG")
        False
    """
    if not isinstance(code, str):
        return False
    if not (2 <= len(code) <= 5):
        return False
    if not code.isupper():
        return False
    if not code.isalpha():
        return False
    return True


def normalize_currency_code(code: str) -> str:
    """
    Нормализует код валюты (приводит к верхнему регистру, убирает пробелы).
    
    Args:
        code: Код валюты для нормализации
        
    Returns:
        Нормализованный код
        
    Raises:
        ValueError: Если код имеет неверный формат
        
    Examples:
        >>> normalize_currency_code("usd")
        'USD'
        >>> normalize_currency_code(" btc ")
        'BTC'
        >>> normalize_currency_code("invalid123")
        Traceback (most recent call last):
        ...
        ValueError: Неверный формат кода валюты: 'invalid123'
    """
    normalized = code.strip().upper()
    if not is_valid_currency_code(normalized):
        raise ValueError(f"Неверный формат кода валюты: '{code}'")
    return normalized


def format_percentage(value: float, precision: int = 2) -> str:
    """
    Форматирует число как процент.
    
    Args:
        value: Значение для форматирования (0.15 = 15%)
        precision: Количество знаков после запятой
        
    Returns:
        Отформатированная строка с процентами
        
    Examples:
        >>> format_percentage(0.1523)
        '15.23%'
        >>> format_percentage(0.5, 0)
        '50%'
        >>> format_percentage(-0.0342)
        '-3.42%'
    """
    percentage = value * 100
    return f"{percentage:.{precision}f}%"


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Обрезает строку до указанной длины с добавлением суффикса.
    
    Args:
        text: Исходная строка
        max_length: Максимальная длина результата
        suffix: Суффикс для обрезанной строки (по умолчанию "...")
        
    Returns:
        Обрезанная строка
        
    Examples:
        >>> truncate_string("Very long wallet name", 15)
        'Very long wa...'
        >>> truncate_string("Short", 10)
        'Short'
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
