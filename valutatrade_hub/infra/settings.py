"""
Реализация Singleton паттерна для загрузки и доступа к настройкам проекта.
"""
import json
from threading import Lock


class SingletonMeta(type):
    """
    Метакласс, который превращает обычный класс в Singleton.
    Он гарантирует, что у класса будет только один экземпляр.
    """
    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]

class SettingsLoader(metaclass=SingletonMeta):
    """
    Singleton для управления конфигурацией приложения.
    Загружает настройки из config.json или использует значения по умолчанию.
    """
    def __init__(self, config_path: str = "config.json"):
        self._config_path = config_path
        self._config = {}
        self.reload()

    def reload(self):
        """Перезагружает конфигурацию из файла."""
        # Значения по умолчанию
        default_config = {
            "DATA_DIR": "data",
            "RATES_TTL_SECONDS": 300,  # 5 минут
            "DEFAULT_BASE_CURRENCY": "USD",
            "LOG_FILE": "logs/actions.log",
            "LOG_LEVEL": "INFO",
        }
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                self._config = {**default_config, **file_config}
        except (FileNotFoundError, json.JSONDecodeError):
            self._config = default_config

    def get(self, key: str, default: any = None) -> any:
        """
        Возвращает значение настройки по ключу.
        
        Пример:
            SettingsLoader().get("DATA_DIR")
        """
        return self._config.get(key, default)

    @property
    def data_dir(self) -> str:
        """Путь к директории с данными."""
        return self.get("DATA_DIR")
