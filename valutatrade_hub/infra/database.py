"""
Реализация Singleton паттерна для управления доступом к базе данных (JSON-файлам).
"""
import json
import os
from typing import Dict, List

# Используем наши кастомные исключения
from ..core.exceptions import BaseWalletException

# Используем модели, чтобы работать с типизированными объектами
from ..core.models import Portfolio, User

# Используем Singleton для настроек
from .settings import SettingsLoader, SingletonMeta


class DatabaseManager(metaclass=SingletonMeta):
    """
    Singleton для управления чтением и записью данных в JSON-файлы.
    """
    def __init__(self):
        settings = SettingsLoader()
        self.data_dir = settings.data_dir
        
        self.users_path = os.path.join(self.data_dir, "users.json")
        self.portfolios_path = os.path.join(self.data_dir, "portfolios.json")
        self.rates_path = os.path.join(self.data_dir, "rates.json")
        
        os.makedirs(self.data_dir, exist_ok=True)

    def _load_data(self, file_path: str, default: any) -> any:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            if default is not None:
                self._save_data(file_path, default)
            return default

    def _save_data(self, file_path: str, data: any) -> None:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except IOError as e:
            raise BaseWalletException(f"Ошибка записи в файл {file_path}: {e}")

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
