"""
Консольный интерфейс приложения Currency Wallet.
Единственная точка входа для пользовательских команд.
"""
import sys

from ..core.currencies import get_all_currency_codes, get_currency

# Импортируем все необходимые компоненты
from ..core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from ..core.usecases import AuthService, PortfolioService, RateService

# Глобальная переменная для хранения сессии
current_user = None

def handle_register(username, password):
    """Обработчик команды register."""
    try:
        auth_service = AuthService()
        user = auth_service.register(username, password)
        print(
            f"✅ Пользователь '{user.username}' успешно зарегистрирован "
            f"(id={user.user_id})."
        )
        print(
            "   Теперь вы можете войти: "
            "login --username YOUR_USERNAME --password YOUR_PASSWORD"
        )
    except ValueError as e:
        print(f"❌ Ошибка регистрации: {e}")
    except Exception as e:
        print(f"❌ Непредвиденная ошибка: {e}")

def handle_sell(currency_code, amount_str):
    """Обработчик команды sell."""
    global current_user
    if not current_user:
        print(
            "❌ Ошибка: Эта команда доступна только для "
            "авторизованных пользователей. Выполните 'login'."
        )
        return

    try:
        amount = float(amount_str)
        # Валидация валюты перед вызовом сервиса
        get_currency(currency_code)

        rate_service = RateService()
        portfolio_service = PortfolioService(rate_service)
        
        # Вызываем метод и ИСПОЛЬЗУЕМ результат
        result = portfolio_service.sell_currency(
            current_user.user_id, currency_code, amount
        )
        print(f"✅ Продажа {amount} {currency_code} выполнена успешно.")
        print(f"   Выручка: {result['proceeds']:.2f} USD")
        print(f"   Баланс {currency_code}: {result['new_balance']:.4f}")

    except InsufficientFundsError as e:
        print(f"❌ Ошибка продажи: {e}")
    except CurrencyNotFoundError as e:
        print(f"❌ Ошибка продажи: {e}")
        print("💡 Поддерживаемые валюты: " + ", ".join(get_all_currency_codes()))
    except ApiRequestError as e:
        print(f"❌ Ошибка получения курса: {e}")
        print("💡 Попробуйте позже или проверьте подключение к сети.")
    except (ValueError, TypeError):
        print("❌ Ошибка: 'amount' должен быть числом (например, 10.5).")
    except Exception as e:
        print(f"❌ Непредвиденная ошибка: {e}")


def main():
    """Парсер команд и точка входа в CLI."""
    args = sys.argv[1:]
    if not args:
        print("Добро пожаловать в Currency Wallet!")
        print("Используйте 'help' для списка команд.")
        return

    command = args[0]
    
    # Здесь будет полноценный парсер аргументов, пока — простая заглушка
    if command == "register":
        # Пример: register --username alice --password 123
        username = args[2]
        password = args[4]
        handle_register(username, password)
    elif command == "sell":
        # Пример: sell --currency BTC --amount 0.5
        # Для теста представим, что пользователь уже залогинен
        global current_user
        from ..core.models import User
        current_user = User(1, 'testuser', 'testpass')

        currency = args[2]
        amount = args[4]
        handle_sell(currency, amount)
    else:
        print(f"Неизвестная команда: {command}")


if __name__ == "__main__":
    main()
