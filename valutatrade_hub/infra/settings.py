"""
Реализация Singleton паттерна для загрузки и доступа к настройкам проекта.

Технологические требования:
- Реализация через метакласс (SingletonMeta)
- Обоснование выбора: метакласс обеспечивает контроль на уровне создания класса,
  что делает невозможным случайное создание второго экземпляра даже при импортах.
  Более явный и контролируемый подход по сравнению с __new__.
- Потокобезопасность не требуется, так как приложение однопоточное (CLI).
"""
import json
from pathlib import Path
from typing import Any


class SingletonMeta(type):
    """
    Метакласс для реализации паттерна Singleton.
    
    Гарантирует, что у класса будет только один экземпляр на протяжении
    всего жизненного цикла приложения.
    
    Выбор метакласса обоснован:
    - Контроль на уровне создания класса
    - Невозможность обхода через повторные импорты
    - Чистый и явный синтаксис использования
    - Не требует переопределения __new__ или __init__ в дочерних классах
    
    Потокобезопасность не реализована, так как приложение однопоточное.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Перехватывает вызов конструктора класса.
        Возвращает существующий экземпляр или создает новый.
        """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class SettingsLoader(metaclass=SingletonMeta):
    """
    Singleton для управления конфигурацией приложения.
    
    Ответственность:
    - Загрузка настроек из config.json
    - Кеширование конфигурации в памяти
    - Предоставление доступа к параметрам через единый интерфейс
    
    Ключи конфигурации:
    - DATA_DIR: путь к директории с данными (users.json, portfolios.json, rates.json)
    - RATES_TTL_SECONDS: время жизни курсов валют в секундах (для кеширования)
    - DEFAULT_BASE_CURRENCY: базовая валюта по умолчанию (USD)
    - LOG_FILE: путь к файлу логов
    - LOG_LEVEL: уровень логирования (INFO, DEBUG, WARNING, ERROR)
    
    Использование в проекте:
    - core/usecases.py: RateService использует RATES_TTL_SECONDS для кеширования
    - infra/database.py: DatabaseManager использует DATA_DIR для путей к JSON
    - cli/interface.py: может использовать LOG_FILE и LOG_LEVEL для логирования
    """
    
    def __init__(self, config_path: str = "config.json"):
        """
        Инициализирует загрузчик настроек.
        
        Args:
            config_path: путь к файлу конфигурации (относительно корня проекта)
        
        Примечание:
            Вызывается только один раз при первом обращении к SettingsLoader().
            Повторные вызовы конструктора будут возвращать тот же экземпляр.
        """
        self._config_path = config_path
        self._config = {}
        self.reload()

    def reload(self):
        """
        Перезагружает конфигурацию из файла.
        
        Используется для:
        - Первоначальной загрузки при создании экземпляра
        - Обновления настроек без перезапуска приложения
        
        Логика:
        1. Определяет значения по умолчанию
        2. Пытается загрузить файл config.json
        3. Объединяет загруженные значения с дефолтными (приоритет у файла)
        4. При ошибке использует только дефолтные значения
        
        Raises:
            Никаких исключений не выбрасывает, молча откатывается к дефолтам
        """
        # Значения по умолчанию
        default_config = {
            "DATA_DIR": "data",
            "RATES_TTL_SECONDS": 300,  # 5 минут
            "DEFAULT_BASE_CURRENCY": "USD",
            "LOG_FILE": "logs/actions.log",
            "LOG_LEVEL": "INFO",
        }
        
        try:
            config_file = Path(self._config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    # Объединяем: приоритет у значений из файла
                    self._config = {**default_config, **file_config}
            else:
                self._config = default_config
        except (FileNotFoundError, json.JSONDecodeError, PermissionError):
            # При любой ошибке используем дефолтные значения
            self._config = default_config

    def get(self, key: str, default: Any = None) -> Any:
        """
        Получает значение настройки по ключу.
        
        Args:
            key: ключ настройки (например, "DATA_DIR")
            default: значение по умолчанию, если ключ не найден
        
        Returns:
            Значение настройки или default, если ключ отсутствует
        
        Примеры использования:
            >>> settings = SettingsLoader()
            >>> data_dir = settings.get("DATA_DIR")
            >>> ttl = settings.get("RATES_TTL_SECONDS", 60)
            >>> unknown = settings.get("UNKNOWN_KEY", "fallback")
        """
        return self._config.get(key, default)

    @property
    def data_dir(self) -> str:
        """
        Путь к директории с данными.
        
        Удобный shortcut для settings.get("DATA_DIR").
        
        Returns:
            Строка с путем к директории данных
        
        Использование:
            >>> settings = SettingsLoader()
            >>> print(settings.data_dir)
            'data'
        """
        return self.get("DATA_DIR")
    
    @property
    def rates_ttl_seconds(self) -> int:
        """
        Время жизни курсов валют в секундах.
        
        Используется RateService для определения, нужно ли обновлять курсы.
        
        Returns:
            Количество секунд
        """
        return self.get("RATES_TTL_SECONDS", 300)
    
    @property
    def default_base_currency(self) -> str:
        """
        Базовая валюта по умолчанию.
        
        Returns:
            Код валюты (например, "USD")
        """
        return self.get("DEFAULT_BASE_CURRENCY", "USD")


# Места использования SettingsLoader в проекте:
#
# 1. valutatrade_hub/core/usecases.py:
#    - RateService.__init__(): self.settings = SettingsLoader()
#    - Использование: ttl = self.settings.rates_ttl_seconds
#
# 2. valutatrade_hub/infra/database.py:
#    - DatabaseManager.__init__(): settings = SettingsLoader()
#    - Использование: self.data_dir = Path(settings.data_dir)
#
# 3. valutatrade_hub/cli/interface.py (будущее):
#    - Настройка логирования: log_file = SettingsLoader().get("LOG_FILE")
