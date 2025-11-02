"""
Основная бизнес-логика приложения.
Содержит сервисы для управления пользователями, портфелями и курсами.
"""
import json
import os
from typing import Dict, List

# Импортируем наши модели данных
from .models import Portfolio, User


class DataManager:
    """
    Отвечает за чтение и запись данных в JSON-файлы.
    Инкапсулирует всю работу с файловой системой.
    """
    def __init__(self, data_folder: str = "data"):
        self.data_folder = data_folder
        self.users_path = os.path.join(data_folder, "users.json")
        self.portfolios_path = os.path.join(data_folder, "portfolios.json")
        self.rates_path = os.path.join(data_folder, "rates.json")
        os.makedirs(self.data_folder, exist_ok=True)

    def _load_data(self, file_path: str, default: any) -> any:
        """Загружает данные из JSON-файла."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def _save_data(self, file_path: str, data: any) -> None:
        """Сохраняет данные в JSON-файл."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    # --- Методы для пользователей ---
    def get_users(self) -> List[User]:
        users_data = self._load_data(self.users_path, [])
        return [User.from_dict(u) for u in users_data]

    def save_users(self, users: List[User]) -> None:
        self._save_data(self.users_path, [u.to_dict() for u in users])

    # --- Методы для портфелей ---
    def get_portfolios(self) -> List[Portfolio]:
        portfolios_data = self._load_data(self.portfolios_path, [])
        return [Portfolio.from_dict(p) for p in portfolios_data]

    def save_portfolios(self, portfolios: List[Portfolio]) -> None:
        self._save_data(self.portfolios_path, [p.to_dict() for p in portfolios])

    # --- Методы для курсов ---
    def get_rates(self) -> Dict:
        return self._load_data(self.rates_path, {})

    def save_rates(self, rates: Dict) -> None:
        self._save_data(self.rates_path, rates)


class AuthService:
    """Сервис для аутентификации и регистрации пользователей."""
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def register(self, username: str, password: str) -> User:
        """Регистрирует нового пользователя."""
        users = self.data_manager.get_users()
        if any(u.username == username for u in users):
            raise ValueError(f"Имя пользователя '{username}' уже занято")

        # Генерация нового user_id
        new_user_id = max([u.user_id for u in users] or [0]) + 1
        
        # Создание пользователя (хеширование пароля происходит в конструкторе)
        new_user = User(user_id=new_user_id, username=username, password=password)
        users.append(new_user)
        self.data_manager.save_users(users)
        
        # Создание пустого портфеля для нового пользователя
        portfolios = self.data_manager.get_portfolios()
        new_portfolio = Portfolio(user_id=new_user_id)
        # Добавим сразу USD кошелек со стартовым капиталом
        new_portfolio.add_currency("USD")
        new_portfolio.get_wallet("USD").deposit(10000)
        portfolios.append(new_portfolio)
        self.data_manager.save_portfolios(portfolios)
        
        return new_user

    def login(self, username: str, password: str) -> User:
        """Аутентифицирует пользователя."""
        users = self.data_manager.get_users()
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
        "EUR_USD": 1.08, "BTC_USD": 60000.0, "RUB_USD": 0.011, "ETH_USD": 3000.0
    }

    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager

    def get_rate(self, from_currency: str, to_currency: str) -> float:
        """Получает курс обмена между двумя валютами."""
        from_currency, to_currency = from_currency.upper(), to_currency.upper()
        if from_currency == to_currency:
            return 1.0
        
        rates_data = self.data_manager.get_rates() or self.FALLBACK_RATES

        # Прямой курс (e.g., EUR_USD)
        pair = f"{from_currency}_{to_currency}"
        if pair in rates_data and "rate" in rates_data[pair]:
            return rates_data[pair]["rate"]
        
        # Обратный курс (e.g., USD_EUR)
        reverse_pair = f"{to_currency}_{from_currency}"
        if reverse_pair in rates_data and "rate" in rates_data[reverse_pair]:
            return 1 / rates_data[reverse_pair]["rate"]
        
        # Кросс-курс через USD
        try:
            from_usd_rate = self.get_rate(from_currency, "USD")
            to_usd_rate = self.get_rate(to_currency, "USD")
            return from_usd_rate / to_usd_rate
        except ValueError:
             raise ValueError(f"Курс {from_currency}→{to_currency} недоступен")


class PortfolioService:
    """Сервис для управления портфелями и кошельками."""
    def __init__(self, data_manager: DataManager, rate_service: RateService):
        self.data_manager = data_manager
        self.rate_service = rate_service

    def get_portfolio(self, user_id: int) -> Portfolio:
        """Находит и возвращает портфель пользователя."""
        portfolios = self.data_manager.get_portfolios()
        portfolio = next((p for p in portfolios if p.user_id == user_id), None)
        if not portfolio:
            raise ValueError("Портфель для пользователя не найден")
        return portfolio

    def buy_currency(self, user_id: int, currency: str, amount: float) -> dict:
        """Покупает валюту для пользователя."""
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")

        portfolio = self.get_portfolio(user_id)
        rate = self.rate_service.get_rate(currency, "USD")
        cost_in_usd = amount * rate
        
        # Списываем USD
        usd_wallet = portfolio.get_wallet("USD")
        if not usd_wallet or usd_wallet.balance < cost_in_usd:
            raise ValueError("Недостаточно USD для покупки")
        usd_wallet.withdraw(cost_in_usd)
        
        # Добавляем купленную валюту
        target_wallet = portfolio.get_wallet(currency)
        if not target_wallet:
            target_wallet = portfolio.add_currency(currency)
        
        old_balance = target_wallet.balance
        target_wallet.deposit(amount)
        
        # Сохраняем изменения
        portfolios = self.data_manager.get_portfolios()
        for i, p in enumerate(portfolios):
            if p.user_id == user_id:
                portfolios[i] = portfolio
                break
        self.data_manager.save_portfolios(portfolios)
        
        return {
            "currency": currency, "amount": amount, "rate": rate,
            "cost": cost_in_usd, "old_balance": old_balance, 
            "new_balance": target_wallet.balance
        }

    def sell_currency(self, user_id: int, currency: str, amount: float) -> dict:
        """Продает валюту пользователя."""
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")

        portfolio = self.get_portfolio(user_id)
        
        # Списываем продаваемую валюту
        target_wallet = portfolio.get_wallet(currency)
        
        # Разделяем проверки для более ясных сообщений об ошибках
        if not target_wallet:
            raise ValueError(f"У вас нет кошелька '{currency}'")

        if target_wallet.balance < amount:
            available_balance = target_wallet.balance
            raise ValueError(
                f"Недостаточно средств: доступно {available_balance} {currency}"
            )
        
        old_balance = target_wallet.balance
        target_wallet.withdraw(amount)
        
        # Начисляем USD
        rate = self.rate_service.get_rate(currency, "USD")
        proceeds_in_usd = amount * rate
        usd_wallet = portfolio.get_wallet("USD")
        if not usd_wallet: # На всякий случай
            usd_wallet = portfolio.add_currency("USD")
        usd_wallet.deposit(proceeds_in_usd)

        # Сохраняем изменения
        portfolios = self.data_manager.get_portfolios()
        for i, p in enumerate(portfolios):
            if p.user_id == user_id:
                portfolios[i] = portfolio
                break
        self.data_manager.save_portfolios(portfolios)

        return {
            "currency": currency,
            "amount": amount,
            "rate": rate,
            "proceeds": proceeds_in_usd,
            "old_balance": old_balance,
            "new_balance": target_wallet.balance,
        }

