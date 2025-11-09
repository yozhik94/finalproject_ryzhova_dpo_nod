"""
Консольный интерфейс приложения Currency Wallet.
Единственная точка входа для пользовательских команд.
"""
import shlex

from ..core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)

# --- ИЗМЕНЕНИЕ: Возвращаем импорт классов ---
from ..core.usecases import (
    AuthService,
    PortfolioService,
    RateService,
)
from ..core.utils import format_currency
from ..parser_service.updater import RatesUpdater

current_user = None


def handle_register(username, password):
    """Обработчик команды register."""
    try:
        auth_service = AuthService()
        user = auth_service.register(username, password)
        print(
            f" Пользователь '{user.username}' успешно зарегистрирован "
            f"(id={user.user_id})."
        )
        print(
            "   Теперь вы можете войти: "
            "login --username YOUR_USERNAME --password YOUR_PASSWORD"
        )
    except ValueError as e:
        print(f" Ошибка регистрации: {e}")
    except Exception as e:
        print(f" Непредвиденная ошибка: {e}")


def handle_login(username, password):
    """Обработчик команды login."""
    global current_user
    try:
        auth_service = AuthService()
        user = auth_service.login(username, password)
        current_user = user
        print(f" Успешный вход для пользователя: {user.username}")
    except ValueError as e:
        print(f" Ошибка входа: {e}")
    except Exception as e:
        print(f" Непредвиденная ошибка: {e}")


def handle_buy(currency_code, amount_str):
    """Обработчик команды buy."""
    try:
        amount = float(amount_str)
        rate_service = RateService()
        portfolio_service = PortfolioService(rate_service)
        result = portfolio_service.buy_currency(
            current_user.user_id, currency_code, amount
        )
        portfolio = portfolio_service.get_portfolio(current_user.user_id)
        usd_wallet = portfolio.get_wallet("USD")
        usd_balance = usd_wallet.balance if usd_wallet else 0.0

        print(
            f" Покупка {format_currency(amount, currency_code)} "
            f"выполнена успешно."
        )
        print(
            f"   Потрачено: {format_currency(result['cost'], 'USD')} "
            f"(курс: {result['rate']})"
        )
        print(
            f"   Новый баланс {currency_code}: "
            f"{format_currency(result['new_balance'], currency_code)}"
        )
        print(f"   Остаток USD: {format_currency(usd_balance, 'USD')}")
    except (InsufficientFundsError, CurrencyNotFoundError, ApiRequestError) as e:
        print(f" Ошибка покупки: {e}")
    except ValueError as e:
        if "could not convert" in str(e).lower():
            print(" Ошибка: 'amount' должен быть числом (например, 10.5).")
        else:
            print(f" Ошибка: {e}")
    except Exception as e:
        print(f" Непредвиденная ошибка: {e}")


def handle_sell(target_currency, amount_str):
    """
    Обработчик команды sell. Продает актив на сумму в целевой валюте.
    """
    try:
        amount_in_target = float(amount_str)
        rate_service = RateService()
        portfolio_service = PortfolioService(rate_service)
        result = portfolio_service.sell_currency(
            current_user.user_id, target_currency, amount_in_target
        )

        asset_sold = result['asset_sold']
        amount_sold_str = format_currency(result['amount_sold'], asset_sold)
        rate_str = (
            f"{result['rate']} {result['target_currency']}/"
            f"{asset_sold}"
        )
        old_balance_str = format_currency(result['old_balance'], asset_sold)
        new_balance_str = format_currency(result['new_balance'], asset_sold)
        proceeds_str = format_currency(result['proceeds'], result['target_currency'])

        print(f"Продажа выполнена: {amount_sold_str} по курсу {rate_str}")
        print("   Изменения в портфеле:")
        print(f"   - {asset_sold}: было {old_balance_str} → стало {new_balance_str}")
        print(f"   Оценочная выручка: {proceeds_str}")

    except (InsufficientFundsError, CurrencyNotFoundError, ValueError) as e:
        print(f" Ошибка продажи: {e}")
    except Exception as e:
        print(f" Непредвиденная ошибка: {e}")


def handle_show_portfolio(base_currency="USD"):
    """Обработчик команды show-portfolio."""
    try:
        rate_service = RateService()
        portfolio_service = PortfolioService(rate_service)
        portfolio = portfolio_service.get_portfolio(current_user.user_id)
        wallets = portfolio.get_all_wallets()

        if not wallets:
            print(f"Портфель пользователя '{current_user.username}' пуст.")
            return

        print(
            f" Портфель пользователя '{current_user.username}' "
            f"(база: {base_currency}):"
        )
        total_value = 0.0
        for wallet in sorted(wallets, key=lambda w: w.currency_code):
            balance_str = format_currency(wallet.balance, wallet.currency_code)
            try:
                rate_data = rate_service.get_rate(
                    wallet.currency_code, base_currency
                )
                rate = rate_data['rate']

                value_in_base = wallet.balance * rate
                total_value += value_in_base
                print(
                    f"   - {wallet.currency_code}: {balance_str}  → "
                    f"{format_currency(value_in_base, base_currency)}"
                )
            except ValueError:
                print(
                    f"   - {wallet.currency_code}: {balance_str}  → (курс недоступен)"
                )

        print("-" * 50)
        print(f"    Общая стоимость: {format_currency(total_value, base_currency)}")
    except Exception as e:
        print(f" Ошибка при отображении портфеля: {e}")


def handle_update_rates(source=None):
    """Обработчик команды update-rates."""
    print("  INFO: Starting rates update...")
    try:
        updater = RatesUpdater()
        result = updater.update_rates(source=source)
        
        for src, info in result["sources"].items():
            name = "ExchangeRate-API" if src == "exchangerate" else src.capitalize()
            if info["success"]:
                print(f" INFO: Fetching from {name}... OK ({info['rates']} rates)")
            else:
                error_msg = info.get('error', 'Unknown error')
                print(f" ERROR: Failed to fetch from {name}: {error_msg}")
        if result["total_rates"] > 0:
            print(f" INFO: Writing {result['total_rates']} rates to data/rates.json...")
        if result["success"]:
            print(
                f" Update successful. Total rates updated: {result['total_rates']}. "
                f"Last refresh: {result['timestamp']}"
            )
        else:
            print("  Update completed with errors. Check logs/actions.log for details.")
    except Exception as e:
        print(f" ERROR: A critical error occurred: {e}")


def handle_show_rates(currency=None, top=None, base=None):
    """Обработчик команды show-rates."""
    try:
        updater = RatesUpdater()
        cache = updater.get_current_rates()
        pairs = {
            k: v for k, v in cache.items()
            if k not in {"source", "last_refresh"} and isinstance(v, dict)
        }
        
        if not pairs:
            print("  Локальный кеш курсов пуст. Выполните 'update-rates'.")
            return
            
        filtered = []
        for k, data in pairs.items():
            f, t = k.split("_")
            if (base and t.upper() != base.upper()) or \
               (currency and f.upper() != currency.upper()):
                continue
            filtered.append((k, data["rate"]))
            
        if not filtered:
            print(f"  Курс для '{(currency or base).upper()}' не найден.")
            return

        filtered.sort(key=lambda item: item[1] if top else item[0], reverse=bool(top))
        if top:
            filtered = filtered[:top]
            
        print(f" Rates from cache (updated at {cache.get('last_refresh')}):")
        for pair, rate in filtered:
            print(f"   - {pair}: {rate}")
    except Exception as e:
        print(f" ERROR: An error occurred: {e}")

def handle_get_rate(from_currency, to_currency):
    """Обработчик для команды get-rate."""
    try:
        rate_service = RateService()
        result = rate_service.get_rate(from_currency, to_currency)
        rate = result["rate"]
        timestamp = result["timestamp"]

        # --- ОТЛАДКА ---
        #print(f"DEBUG interface: timestamp received: {timestamp}")
        #print(f"DEBUG interface: type of timestamp: {type(timestamp)}")

        reverse_result = rate_service.get_rate(to_currency, from_currency)
        reverse_rate = reverse_result["rate"]

        time_str = str(timestamp) # <-- Упрощаем до простого вывода строки

        print(
            f"Курс {from_currency.upper()}→{to_currency.upper()}: {rate:.8f} "
            f"(обновлено: {time_str})" # <--- Выводим как есть
        )
        print(
            f"Обратный курс {to_currency.upper()}→{from_currency.upper()}: "
            f"{reverse_rate:.2f}"
        )
    except (ValueError, CurrencyNotFoundError) as e:
        print(f" Ошибка получения курса: {e}")
    except Exception as e:
        print(f" Непредвиденная ошибка: {e}")


def process_command(args):
    """Новая функция для обработки одной команды."""
    global current_user
    if not args:
        return
    command = args[0]
    try:
        if command == "register":
            handle_register(args[2], args[4])
        elif command == "login":
            handle_login(args[2], args[4])
        elif command in ["buy", "sell", "show-portfolio"]:
            if not current_user:
                print(" Ошибка: для этой команды требуется аутентификация. "
                      "Используйте 'login'.")
                return
            if command == "buy":
                handle_buy(args[2], args[4])
            elif command == "sell":
                handle_sell(args[2], args[4])
            elif command == "show-portfolio":
                base = "USD"
                if len(args) > 1 and args[1] == "--base":
                    base = args[2].upper()
                handle_show_portfolio(base)
        elif command == "update-rates":
            source = None
            if len(args) > 1 and args[1] == "--source":
                source = args[2].lower()
            handle_update_rates(source)
        elif command == "show-rates":
            params = {
                args[i].lstrip("-"): (
                    int(args[i + 1]) if args[i] == "--top" else args[i + 1]
                )
                for i in range(1, len(args), 2)
            }
            handle_show_rates(**params)
        elif command == "get-rate":
            handle_get_rate(
                args[args.index("--from") + 1], args[args.index("--to") + 1]
            )
        elif command == "exit":
            return "exit"
        else:
            print(f" Неизвестная команда: {command}")
    except (IndexError, ValueError) as e:
        print(f" Ошибка в аргументах команды '{command}': {e}. Используйте 'help'.")


def main():
    """Главная функция, запускающая интерактивный цикл."""
    from ..infra.settings import SettingsLoader
    from ..logging_config import setup_logging
    
    settings = SettingsLoader()
    setup_logging(
        log_file=settings.get("LOG_FILE", "logs/actions.log"),
        log_level=settings.get("LOG_LEVEL", "INFO"),
    )
    
    print(" Добро пожаловать в ValutaTrade Hub!")
    print(" Введите 'exit', чтобы выйти.")
    
    while True:
        try:
            line = input("> ")
            if not line:
                continue
            args = shlex.split(line)
            if process_command(args) == "exit":
                break
        except KeyboardInterrupt:
            print("\nВыход из приложения.")
            break
        except Exception as e:
            print(f"Критическая ошибка: {e}")


if __name__ == "__main__":
    main()















