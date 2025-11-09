"""
Модели данных для приложения Currency Wallet.
Содержит классы User, Wallet и Portfolio с методами сериализации.
"""


import hashlib
import secrets
from datetime import datetime
from typing import Dict, List, Optional


class User:
    """
    Представляет пользователя системы.

    Attributes:
        _user_id: Уникальный идентификатор пользователя
        _username: Имя пользователя
        _hashed_password: Хешированный пароль
        _salt: Соль для хеширования пароля
        _registration_date: Дата регистрации пользователя
    """

    def __init__(
        self,
        user_id: int,
        username: str,
        password: str,
        salt: Optional[str] = None,
        hashed_password: Optional[str] = None,
        registration_date: Optional[datetime] = None,
    ):
        """
        Инициализирует нового пользователя.

        Args:
            user_id: Уникальный идентификатор
            username: Имя пользователя (не менее 1 символа)
            password: Пароль в открытом виде (не менее 4 символов),
                      не используется при загрузке из БД.
            salt: Соль для хеширования (генерируется автоматически)
            hashed_password: Готовый хеш (для загрузки из БД)
            registration_date: Дата регистрации (текущая дата по умолчанию)

        Raises:
            ValueError: Если имя пустое или пароль короче 4 символов
        """
        if not username or len(username.strip()) == 0:
            raise ValueError("Имя пользователя не может быть пустым")
        if not hashed_password and len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        self._user_id = user_id
        self._username = username.strip()
        self._registration_date = registration_date or datetime.now()

        if hashed_password and salt:
            self._salt = salt
            self._hashed_password = hashed_password
        else:
            self._salt = salt or secrets.token_hex(8)
            self._hashed_password = self._hash_password(password, self._salt)

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Хеширует пароль с использованием соли."""
        return hashlib.sha256((password + salt).encode()).hexdigest()

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username
        
    @property
    def password(self) -> str:
        # Это свойство нужно для обратной совместимости с usecases.py
        # В идеале, его нужно будет удалить и везде использовать verify_password
        # Но для быстрого исправления - это лучший вариант.
        return self._hashed_password

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @username.setter
    def username(self, value: str) -> None:
        if not value or len(value.strip()) == 0:
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    def get_user_info(self) -> dict:
        """Возвращает информацию о пользователе (без пароля)."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль пользователя."""
        if len(new_password) < 4:
            raise ValueError("Новый пароль должен быть не короче 4 символов")
        self._salt = secrets.token_hex(8)
        self._hashed_password = self._hash_password(new_password, self._salt)

    def verify_password(self, password: str) -> bool:
        """Проверяет введённый пароль на совпадение."""
        return self._hash_password(password, self._salt) == self._hashed_password

    def to_dict(self) -> dict:
        """Сериализует объект User в словарь для сохранения в JSON."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "salt": self._salt,
            "hashed_password": self._hashed_password,
            "registration_date": self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Создает объект User из словаря (десериализация из JSON)."""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            password="",
            salt=data["salt"],
            hashed_password=data["hashed_password"],
            registration_date=datetime.fromisoformat(data["registration_date"]),
        )

    def __repr__(self):
        return f"User(id={self._user_id}, username='{self._username}')"


class Wallet:
    """Представляет кошелёк для одной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0):
        """
        Инициализирует кошелек с указанной валютой.

        Args:
            currency_code: Код валюты (например, 'USD', 'EUR', 'BTC')
            balance: Начальный баланс (по умолчанию 0.0)

        Raises:
            ValueError: Если баланс отрицательный
        """
        if balance < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self.currency_code = currency_code.upper()
        self._balance = float(balance)

    @property
    def balance(self) -> float:
        """Возвращает текущий баланс кошелька."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Устанавливает баланс кошелька с валидацией."""
        if not isinstance(value, (int, float)):
            raise TypeError("Значение баланса должно быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """
        Пополняет кошелек на указанную сумму.

        Args:
            amount: Сумма пополнения

        Raises:
            ValueError: Если сумма не положительная
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError(
                "Сумма пополнения должна быть положительным числом"
            )
        self._balance += amount

    def withdraw(self, amount: float) -> None:
        """
        Списывает указанную сумму с кошелька.

        Args:
            amount: Сумма для списания

        Raises:
            ValueError: Если сумма не положительная или превышает баланс
        """
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Сумма снятия должна быть положительным числом")
        if amount > self._balance:
            raise ValueError(
                f"Недостаточно средств. Доступно: {self._balance}"
            )
        self._balance -= amount

    def get_balance_info(self) -> str:
        """Возвращает строковое представление баланса."""
        return f"Баланс {self.currency_code}: {self._balance}"

    # --- Методы сериализации для JSON ---
    def to_dict(self) -> dict:
        """
        Сериализует объект Wallet в словарь для сохранения в JSON.

        Returns:
            dict: Словарь с данными кошелька
        """
        return {
            "currency_code": self.currency_code,
            "balance": self._balance
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Wallet':
        """
        Создает объект Wallet из словаря (десериализация из JSON).

        Args:
            data: Словарь с данными кошелька

        Returns:
            Wallet: Восстановленный объект кошелька
        """
        return cls(
            currency_code=data["currency_code"],
            balance=data["balance"]
        )

    def __repr__(self):
        return f"Wallet({self.currency_code}, balance={self._balance:.2f})"


class Portfolio:
    """Представляет портфель пользователя (все его кошельки)."""

    # Фиксированные курсы для упрощения
    EXCHANGE_RATES = {
        "USD": 1.0,
        "EUR": 1.08,
        "BTC": 60000.0,
        "ETH": 3000.0,
        "RUB": 0.011,
    }

    def __init__(
        self,
        user_id: int,
        wallets: Optional[Dict[str, Wallet]] = None
    ):
        """
        Инициализирует портфель для указанного пользователя.

        Args:
            user_id: ID пользователя, которому принадлежит портфель
            wallets: Словарь существующих кошельков (для загрузки из БД)
        """
        self._user_id = user_id
        self._wallets: Dict[str, Wallet] = wallets if wallets else {}

    @property
    def user_id(self) -> int:
        """Возвращает ID пользователя."""
        return self._user_id

    @property
    def wallets(self) -> Dict[str, Wallet]:
        """Возвращает копию словаря кошельков."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """
        Добавляет новый кошелек для указанной валюты.
        """
        code = currency_code.upper()
        if code in self._wallets:
            raise ValueError(f"Кошелёк для валюты {code} уже существует")
        wallet = Wallet(currency_code=code)
        self._wallets[code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Optional[Wallet]:
        """
        Возвращает кошелек для указанной валюты.
        """
        return self._wallets.get(currency_code.upper())

    def get_all_wallets(self) -> List[Wallet]:
        """
        Возвращает список всех кошельков в портфеле.
        """
        return list(self._wallets.values())

    def get_total_value(self, base_currency: str = "USD") -> float:
        """
        Вычисляет общую стоимость портфеля в указанной валюте.
        """
        base_code = base_currency.upper()
        if base_code not in self.EXCHANGE_RATES:
            raise ValueError(f"Неизвестная базовая валюта: {base_code}")

        total_value = 0.0
        base_rate = self.EXCHANGE_RATES[base_code]

        for wallet in self._wallets.values():
            if wallet.currency_code in self.EXCHANGE_RATES:
                # Конвертируем баланс в USD, затем в базовую валюту
                usd_value = (
                    wallet.balance * self.EXCHANGE_RATES[wallet.currency_code]
                )
                total_value += usd_value / base_rate
        return round(total_value, 2)

    # --- Методы сериализации для JSON ---
    def to_dict(self) -> dict:
        """
        Сериализует объект Portfolio в словарь для сохранения в JSON.
        """
        return {
            "user_id": self._user_id,
            "wallets": [
                wallet.to_dict() for wallet in self._wallets.values()
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Portfolio':
        """
        Создает объект Portfolio из словаря (десериализация из JSON).
        """
        wallets_dict = {}
        for wallet_data in data.get("wallets", []):
            wallet = Wallet.from_dict(wallet_data)
            wallets_dict[wallet.currency_code] = wallet

        return cls(user_id=data["user_id"], wallets=wallets_dict)

    def __repr__(self):
        wallet_count = len(self._wallets)
        return f"Portfolio(user_id={self._user_id}, wallets={wallet_count})"

