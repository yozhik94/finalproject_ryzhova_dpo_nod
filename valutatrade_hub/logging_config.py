"""
Конфигурация системы логирования для ValutaTrade Hub.

Настраивает форматы логов, уровни, ротацию файлов и обработчики.
"""
import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_file: str = "logs/actions.log", log_level: str = "INFO"):
    """
    Настраивает систему логирования для приложения.
    
    Args:
        log_file: Путь к файлу логов (относительно корня проекта)
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
    
    Конфигурация:
        - Человекочитаемый формат (не JSON)
        - Ротация файлов: размер 10 MB, хранить 5 файлов
        - Вывод в консоль + файл
        - Отдельный логгер для actions (valutatrade.actions)
    
    Формат записи:
        2025-11-03 21:50:00 INFO valutatrade.actions: BUY user_id=1 ...
    """
    # Создаем директорию для логов, если её нет
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Преобразуем строковый уровень в константу logging
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Формат логов (человекочитаемый)
    log_format = (
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Создаем форматтер
    formatter = logging.Formatter(log_format, datefmt=date_format)
    
    # === Обработчик для файла с ротацией ===
    # maxBytes: 10 MB = 10 * 1024 * 1024
    # backupCount: хранить 5 архивных файлов (actions.log.1, .2, .3, .4, .5)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    
    # === Обработчик для консоли (опционально) ===
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # В консоль только WARNING и ERROR
    console_handler.setFormatter(formatter)
    
    # === Настройка логгера для actions ===
    actions_logger = logging.getLogger("valutatrade.actions")
    actions_logger.setLevel(numeric_level)
    actions_logger.addHandler(file_handler)
    actions_logger.addHandler(console_handler)
    
    # Предотвращаем дублирование логов в root logger
    actions_logger.propagate = False
    
    # === Настройка root logger (для остального приложения) ===
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Если у root logger ещё нет обработчиков, добавляем
    if not root_logger.handlers:
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    # Логируем успешную инициализацию
    actions_logger.info("=" * 60)
    actions_logger.info("Logging system initialized")
    actions_logger.info(f"Log file: {log_file}")
    actions_logger.info(f"Log level: {log_level}")
    actions_logger.info("=" * 60)
