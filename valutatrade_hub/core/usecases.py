"""
Основная бизнес-логика приложения с логированием операций.
Содержит сервисы для управления пользователями, портфелями и курсами.
"""
from datetime import datetime

from ..core.currencies import get_currency
from ..core.exceptions import InsufficientFundsError
from ..core.models import Portfolio, User
from ..core.utils import validate_amount
from ..decorators import log_action
from ..infra.database import DatabaseManager
from ..infra.settings import SettingsLoader


class AuthService:
    """Сервис для аутентификации и регистрации пользователей."""

    def __init__(self):
        self.db = DatabaseManager()

    def find_user_by_username(self, username: str) -> User | None:
        """Вспомогательный метод для поиска пользователя по имени."""
        users = self.db.get_users()
        return next((u for u in users if u.username == username), None)

    @log_action(action_type="REGISTER", verbose=True)
    def register(self, username: str, password: str) -> User:
        """Регистрирует нового пользователя."""
        if self.find_user_by_username(username):
            raise ValueError(f"Имя пользователя '{username}' уже занято")
        users = self.db.get_users()
        new_user_id = max([u.user_id for u in users] or [0]) + 1
        new_user = User(
            user_id=new_user_id, username=username, password=password
        )
        users.append(new_user)
        self.db.save_users(users)
        portfolios = self.db.get_portfolios()
        new_portfolio = Portfolio(user_id=new_user_id)
        new_portfolio.add_currency("USD")
        new_portfolio.get_wallet("USD").deposit(10000)
        portfolios.append(new_portfolio)
        self.db.save_portfolios(portfolios)
        return new_user

    @log_action(action_type="LOGIN", verbose=True)
    def login(self, username: str, password: str) -> User:
        """Аутентифицирует пользователя."""
        user = self.find_user_by_username(username)
        if not user:
            raise ValueError(f"Пользователь '{username}' не найден")
        if not user.verify_password(password):
            raise ValueError("Неверный пароль")
        return user


class RateService:
    """Сервис для получения курсов валют."""

    FALLBACK_RATES = {
        "EUR_USD": {"rate": 1.08},
        "BTC_USD": {"rate": 60000.0},
        "RUB_USD": {"rate": 0.011},
        "ETH_USD": {"rate": 3000.0},
    }

    def __init__(self):
        self.db = DatabaseManager()
        self.settings = SettingsLoader()

    def get_rate(
        self, from_currency: str, to_currency: str, depth: int = 0
    ) -> dict:
        """Получает курс обмена и временную метку, читая файл каждый раз."""
        rates_data = self.db.get_rates() or self.FALLBACK_RATES

        # ---> PRINT ДЛЯ ОТЛАДКИ <---
        #print(f"DEBUG: rates_data in get_rate (depth={depth}): {rates_data}")

        if depth > 2:
            msg = f"Превышена глубина рекурсии для {from_currency}→{to_currency}"
            raise ValueError(msg)

        from_currency, to_currency = from_currency.upper(), to_currency.upper()
        get_currency(from_currency)
        get_currency(to_currency)

        if from_currency == to_currency:
            return {"rate": 1.0, "timestamp": datetime.now().isoformat()}

        #timestamp = rates_data.get("last_refresh", "N/A")
        try:
            timestamp = rates_data["last_refresh"]
        except KeyError:
            print("DEBUG: KeyError! Ключ 'last_refresh' НЕ НАЙДЕН.")
            timestamp = "N/A"
        pair = f"{from_currency}_{to_currency}"
        if pair in rates_data and isinstance(rates_data.get(pair), dict):
            return {"rate": rates_data[pair]["rate"], "timestamp": timestamp}

        reverse_pair = f"{to_currency}_{from_currency}"
        if reverse_pair in rates_data and isinstance(
            rates_data.get(reverse_pair), dict
        ):
            return {
                "rate": 1 / rates_data[reverse_pair]["rate"],
                "timestamp": timestamp,
            }

        if from_currency != "USD" and to_currency != "USD":
            try:
                from_usd = self.get_rate(from_currency, "USD", depth + 1)
                to_usd = self.get_rate(to_currency, "USD", depth + 1)

                valid_ts = [
                    ts
                    for ts in [from_usd["timestamp"], to_usd["timestamp"]]
                    if ts != "N/A"
                ]
                cross_ts = min(valid_ts) if valid_ts else "N/A"

                return {
                    "rate": from_usd["rate"] / to_usd["rate"],
                    "timestamp": cross_ts,
                }
            except (ValueError, TypeError):
                pass

        raise ValueError(f"Курс {from_currency}→{to_currency} недоступен")


class PortfolioService:
    """Сервис для управления портфелями."""

    def __init__(self, rate_service: RateService):
        self.db = DatabaseManager()
        self.rate_service = rate_service

    def get_portfolio(self, user_id: int) -> Portfolio:
        """Находит и возвращает портфель пользователя."""
        portfolios = self.db.get_portfolios()
        portfolio = next((p for p in portfolios if p.user_id == user_id), None)
        if not portfolio:
            raise ValueError("Портфель для пользователя не найден")
        return portfolio

    @log_action(action_type="BUY", verbose=True)
    def buy_currency(self, user_id: int, currency: str, amount: float) -> dict:
        """Покупает валюту для пользователя."""
        if not validate_amount(amount, min_value=1e-6):
            raise ValueError("Сумма покупки должна быть положительным числом")

        get_currency(currency)
        portfolio = self.get_portfolio(user_id)
        rate_data = self.rate_service.get_rate(currency, "USD")
        rate = rate_data["rate"]
        cost_in_usd = amount * rate
        usd_wallet = portfolio.get_wallet("USD")

        if not usd_wallet or usd_wallet.balance < cost_in_usd:
            available = usd_wallet.balance if usd_wallet else 0.0
            raise InsufficientFundsError(
                available=available, required=cost_in_usd, code="USD"
            )

        usd_wallet.withdraw(cost_in_usd)

        target_wallet = portfolio.get_wallet(currency)
        if not target_wallet:
            target_wallet = portfolio.add_currency(currency)

        old_balance = target_wallet.balance
        target_wallet.deposit(amount)

        portfolios = self.db.get_portfolios()
        for i, p in enumerate(portfolios):
            if p.user_id == user_id:
                portfolios[i] = portfolio
                break
        self.db.save_portfolios(portfolios)

        return {
            "currency": currency,
            "amount": amount,
            "rate": rate,
            "cost": cost_in_usd,
            "old_balance": old_balance,
            "new_balance": target_wallet.balance,
        }

    @log_action(action_type="SELL", verbose=True)
    def sell_currency(
        self, user_id: int, target_currency: str, amount_in_target: float
    ) -> dict:
        """Продает актив из портфеля на указанную сумму в целевой валюте."""
        if not validate_amount(amount_in_target, min_value=0.01):
            raise ValueError("Сумма продажи должна быть положительным числом")

        get_currency(target_currency)
        portfolio = self.get_portfolio(user_id)

        asset_to_sell = None
        for wallet in portfolio.get_all_wallets():
            if wallet.currency_code.upper() != target_currency.upper():
                asset_to_sell = wallet.currency_code
                break

        if not asset_to_sell:
            raise ValueError("В портфеле нет активов для продажи.")

        target_wallet = portfolio.get_wallet(asset_to_sell)
        rate_data = self.rate_service.get_rate(asset_to_sell, target_currency)
        rate = rate_data["rate"]
        if rate == 0:
            raise ValueError(
                f"Курс для {asset_to_sell} равен нулю, продажа невозможна"
            )

        amount_to_sell = amount_in_target / rate

        if target_wallet.balance < amount_to_sell:
            raise InsufficientFundsError(
                available=target_wallet.balance,
                required=amount_to_sell,
                code=asset_to_sell,
            )

        old_balance = target_wallet.balance
        target_wallet.withdraw(amount_to_sell)

        destination_wallet = portfolio.get_wallet(target_currency)
        if not destination_wallet:
            destination_wallet = portfolio.add_currency(target_currency)
        destination_wallet.deposit(amount_in_target)

        portfolios = self.db.get_portfolios()
        for i, p in enumerate(portfolios):
            if p.user_id == user_id:
                portfolios[i] = portfolio
                break
        self.db.save_portfolios(portfolios)

        return {
            "asset_sold": asset_to_sell,
            "amount_sold": amount_to_sell,
            "rate": rate,
            "proceeds": amount_in_target,
            "target_currency": target_currency,
            "old_balance": old_balance,
            "new_balance": target_wallet.balance,
        }











