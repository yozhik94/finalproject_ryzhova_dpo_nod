"""
Конфигурация системы логирования для ValutaTrade Hub.

Настраивает форматы логов, уровни, ротацию файлов и обработчики.
"""
import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_file: str = "logs/actions.log", log_level: str = "INFO"):
    """
    Настраивает единую систему логирования для всего приложения.
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # === 1. Настройка корневого логгера (root) ===
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Очищаем все существующие обработчики, чтобы избежать дублирования
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # === 2. Форматтеры ===
    # Подробный формат для файла
    file_formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Простой формат для консоли (только само сообщение)
    console_formatter = logging.Formatter("%(message)s")

    # === 3. Обработчик для файла ===
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)  # Пишем в файл все, начиная с INFO
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # === 4. Обработчик для консоли ===
    # Выводит только сообщения с уровнем WARNING и выше
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(console_formatter) # Используем простой формат
    root_logger.addHandler(console_handler)

    # === 5. Отдельная настройка для логгера декоратора ===
    # Чтобы его сообщения ERROR не попадали в консоль
    actions_logger = logging.getLogger("valutatrade.actions")
    actions_logger.propagate = False  # Отключаем проброс наверх
    actions_logger.setLevel(numeric_level)
    # Добавляем ТОЛЬКО файловый обработчик
    action_file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    action_file_handler.setFormatter(file_formatter)
    actions_logger.addHandler(action_file_handler)


    # Логируем успешную инициализацию (используем actions_logger)
    logging.getLogger("valutatrade.actions").info("=" * 60)
    logging.getLogger("valutatrade.actions").info("Logging system initialized")
    logging.getLogger("valutatrade.actions").info(f"Log file: {log_file}")
    logging.getLogger("valutatrade.actions").info(f"Log level: {log_level}")
    logging.getLogger("valutatrade.actions").info("=" * 60)


