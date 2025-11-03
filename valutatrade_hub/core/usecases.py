"""
Основная бизнес-логика приложения с логированием операций.
Содержит сервисы для управления пользователями, портфелями и курсами.
"""


# Импортируем кастомные исключения
# Импортируем валидацию валют
from ..core.currencies import get_currency
from ..core.exceptions import CurrencyNotFoundError, InsufficientFundsError

# Импортируем наши модели данных
from ..core.models import Portfolio, User

# Импортируем декоратор для логирования (из корня valutatrade_hub/)
from ..decorators import log_action

# Импортируем синглтоны из инфраструктурного слоя
from ..infra.database import DatabaseManager
from ..infra.settings import SettingsLoader


class AuthService:
    """Сервис для аутентификации и регистрации пользователей."""
    def __init__(self):
        # Получаем единственный экземпляр DatabaseManager
        self.db = DatabaseManager()

    @log_action(action_type="REGISTER", verbose=True)
    def register(self, username: str, password: str) -> User:
        """Регистрирует нового пользователя."""
        users = self.db.get_users()
        if any(u.username == username for u in users):
            raise ValueError(f"Имя пользователя '{username}' уже занято")

        # Генерация нового user_id
        new_user_id = max([u.user_id for u in users] or [0]) + 1
        
        # Создание пользователя (хеширование пароля происходит в конструкторе)
        new_user = User(user_id=new_user_id, username=username, password=password)
        users.append(new_user)
        self.db.save_users(users)
        
        # Создание пустого портфеля для нового пользователя
        portfolios = self.db.get_portfolios()
        new_portfolio = Portfolio(user_id=new_user_id)
        # Добавим сразу USD кошелек со стартовым капиталом
        new_portfolio.add_currency("USD")
        new_portfolio.get_wallet("USD").deposit(10000)
        portfolios.append(new_portfolio)
        self.db.save_portfolios(portfolios)
        
        return new_user

    @log_action(action_type="LOGIN", verbose=True)
    def login(self, username: str, password: str) -> User:
        """Аутентифицирует пользователя."""
        users = self.db.get_users()
        user = next((u for u in users if u.username == username), None)
        
        if not user:
            raise ValueError(f"Пользователь '{username}' не найден")
        
        if not user.verify_password(password):
            raise ValueError("Неверный пароль")
            
        return user


class RateService:
    """Сервис для получения курсов валют (пока заглушка)."""
    # Фиксированные курсы как запасной вариант
    FALLBACK_RATES = {
        "EUR_USD": {"rate": 1.08}, 
        "BTC_USD": {"rate": 60000.0}, 
        "RUB_USD": {"rate": 0.011}, 
        "ETH_USD": {"rate": 3000.0}
    }

    def __init__(self):
        # Получаем единственные экземпляры синглтонов
        self.db = DatabaseManager()
        self.settings = SettingsLoader()

    def get_rate(self, from_currency: str, to_currency: str, depth: int = 0) -> float:
        """
        Получает курс обмена между двумя валютами с защитой от рекурсии.
        
        Args:
            from_currency: Код валюты источника (например, 'BTC')
            to_currency: Код валюты назначения (например, 'USD')
            depth: Глубина рекурсии (для защиты от циклов)
            
        Returns:
            float: Курс обмена
            
        Raises:
            CurrencyNotFoundError: Если валюта не найдена
            ValueError: Если курс недоступен или превышена глубина рекурсии
        """
        if depth > 2:
            raise ValueError(
                f"Превышена глубина рекурсии для {from_currency}→{to_currency}"
            )
        
        from_currency, to_currency = from_currency.upper(), to_currency.upper()
        
        # Валидация валют через currencies.py
        get_currency(from_currency)
        get_currency(to_currency)
        
        if from_currency == to_currency:
            return 1.0
        
        rates_data = self.db.get_rates() or self.FALLBACK_RATES
        
        # 1. Прямой курс
        pair = f"{from_currency}_{to_currency}"
        if pair in rates_data and "rate" in rates_data[pair]:
            return rates_data[pair]["rate"]
        
        # 2. Обратный курс
        reverse_pair = f"{to_currency}_{from_currency}"
        if reverse_pair in rates_data and "rate" in rates_data[reverse_pair]:
            return 1 / rates_data[reverse_pair]["rate"]
        
        # 3. Кросс-курс через USD
        if from_currency != "USD" and to_currency != "USD":
            try:
                from_usd_rate = self.get_rate(from_currency, "USD", depth + 1)
                to_usd_rate = self.get_rate("USD", to_currency, depth + 1)
                return from_usd_rate * to_usd_rate
            except ValueError:
                pass
        
        # 4. Если ничего не найдено
        raise ValueError(f"Курс {from_currency}→{to_currency} недоступен")


class PortfolioService:
    """Сервис для управления портфелями и кошельками."""
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
        """
        Покупает валюту для пользователя с логированием операции.
        
        Args:
            user_id: ID пользователя
            currency: Код валюты для покупки
            amount: Количество валюты для покупки
            
        Returns:
            dict: Детали операции покупки
            
        Raises:
            ValueError: Если amount <= 0
            CurrencyNotFoundError: Если валюта не найдена
            InsufficientFundsError: Если недостаточно USD
        """
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")

        # Валидация валюты
        get_currency(currency)

        portfolio = self.get_portfolio(user_id)
        rate = self.rate_service.get_rate(currency, "USD")
        cost_in_usd = amount * rate
        
        # Проверка средств
        usd_wallet = portfolio.get_wallet("USD")
        if not usd_wallet:
            raise InsufficientFundsError(
                available=0.0,
                required=cost_in_usd,
                code="USD"
            )
        
        if usd_wallet.balance < cost_in_usd:
            raise InsufficientFundsError(
                available=usd_wallet.balance,
                required=cost_in_usd,
                code="USD"
            )
        
        # Списываем USD
        usd_wallet.withdraw(cost_in_usd)
        
        # Добавляем купленную валюту
        target_wallet = portfolio.get_wallet(currency)
        if not target_wallet:
            target_wallet = portfolio.add_currency(currency)
        
        old_balance = target_wallet.balance
        target_wallet.deposit(amount)
        
        # Сохранение
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
            "new_balance": target_wallet.balance
        }

    @log_action(action_type="SELL", verbose=True)
    def sell_currency(self, user_id: int, currency: str, amount: float) -> dict:
        """
        Продает валюту пользователя с логированием операции.
        
        Args:
            user_id: ID пользователя
            currency: Код валюты для продажи
            amount: Количество для продажи
            
        Returns:
            dict: Детали операции продажи
            
        Raises:
            ValueError: Если amount <= 0
            CurrencyNotFoundError: Если валюта не найдена
            InsufficientFundsError: Если недостаточно средств
        """
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")

        # Валидация валюты
        get_currency(currency)

        portfolio = self.get_portfolio(user_id)
        target_wallet = portfolio.get_wallet(currency)
        
        if not target_wallet:
            raise CurrencyNotFoundError(currency)

        if target_wallet.balance < amount:
            raise InsufficientFundsError(
                available=target_wallet.balance,
                required=amount,
                code=currency
            )
        
        old_balance = target_wallet.balance
        target_wallet.withdraw(amount)
        
        # Получаем курс и начисляем USD
        rate = self.rate_service.get_rate(currency, "USD")
        proceeds_in_usd = amount * rate
        
        usd_wallet = portfolio.get_wallet("USD")
        if not usd_wallet:
            usd_wallet = portfolio.add_currency("USD")
        usd_wallet.deposit(proceeds_in_usd)

        # Сохранение
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
            "proceeds": proceeds_in_usd,
            "old_balance": old_balance,
            "new_balance": target_wallet.balance,
        }
