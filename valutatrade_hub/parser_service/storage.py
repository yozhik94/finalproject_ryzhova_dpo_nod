"""
Модуль для управления хранилищем курсов валют.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import ParserConfig

logger = logging.getLogger(__name__)


class RatesStorage:
    """Менеджер хранилища курсов валют."""

    def __init__(self, config: ParserConfig):
        self.config = config

    @staticmethod
    def _generate_rate_id(
        from_currency: str, to_currency: str, timestamp: datetime
    ) -> str:
        """Генерирует уникальный идентификатор для записи курса."""
        timestamp_str = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        return f"{from_currency}_{to_currency}_{timestamp_str}"

    def save_to_history(
        self,
        rates_data: Dict[str, Dict[str, Any]],
        source: str,
        timestamp: Optional[datetime] = None,
    ) -> int:
        """Сохраняет курсы в файл истории."""
        if timestamp is None:
            timestamp = datetime.utcnow()

        history = self._read_history()
        existing_ids = {r.get("id") for r in history}
        added_count = 0

        for pair_key, data in rates_data.items():
            parts = pair_key.split("_")
            if len(parts) != 2:
                logger.warning(f"Invalid pair key format: {pair_key}")
                continue

            from_currency, to_currency = parts
            record_id = self._generate_rate_id(
                from_currency, to_currency, timestamp
            )

            if record_id in existing_ids:
                continue

            record = {
                "id": record_id,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": data["rate"],
                "timestamp": timestamp.isoformat() + "Z",
                "source": source,
                "meta": data.get("meta", {}),
            }
            history.append(record)
            added_count += 1

        if added_count > 0:
            self._write_history(history)
            logger.info(
                f"Saved {added_count} new records to history from {source}"
            )
        return added_count

    def update_rates_cache(
        self,
        rates_data: Dict[str, Dict[str, Any]],
        source: str,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Обновляет кеш актуальных курсов в ПРАВИЛЬНОМ 'плоском' формате.
        
        Формат согласно заданию:
        {
          "BTC_USD": {"rate": 102455.0, "updated_at": "..."},
          "ETH_USD": {"rate": 3443.55, "updated_at": "..."},
          "source": "ParserService",
          "last_refresh": "..."
        }
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        logger.info("Updating rates cache with the correct flat structure.")

        # 1. Создаем пустой словарь для итогового JSON
        final_json_data = {}

        # 2. Добавляем каждую пару валют напрямую в словарь (НЕ в "pairs"!)
        for pair_key, data in rates_data.items():
            final_json_data[pair_key] = {
                "rate": data["rate"],
                "updated_at": timestamp.isoformat() + "Z",
            }

        # 3. Добавляем метаданные на верхний уровень
        final_json_data["source"] = source
        final_json_data["last_refresh"] = timestamp.isoformat() + "Z"

        # 4. Сохраняем итоговый JSON
        self._write_rates_cache(final_json_data)
        logger.info(f"Updated {len(rates_data)} rates in cache with flat format.")

    def get_rates_cache(self) -> Dict:
        """Получает текущий кеш курсов."""
        return self._read_rates_cache()

    def get_history(
        self,
        from_currency: Optional[str] = None,
        to_currency: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """Получает записи из истории с возможностью фильтрации."""
        history = self._read_history()
        if from_currency:
            history = [
                r for r in history if r.get("from_currency") == from_currency
            ]
        if to_currency:
            history = [
                r for r in history if r.get("to_currency") == to_currency
            ]

        history.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return history[:limit] if limit else history

    def _read_history(self) -> List[Dict]:
        """Читает файл истории exchange_rates.json."""
        if not self.config.HISTORY_FILE_PATH.exists():
            return []
        try:
            with open(
                self.config.HISTORY_FILE_PATH, "r", encoding="utf-8"
            ) as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_history(self, history: List[Dict]) -> None:
        """Атомарно записывает данные в файл истории."""
        self._atomic_write(self.config.HISTORY_FILE_PATH, history)

    def _read_rates_cache(self) -> Dict:
        """Читает файл кеша rates.json."""
        if not self.config.RATES_FILE_PATH.exists():
            return {}
        try:
            with open(self.config.RATES_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _write_rates_cache(self, cache: Dict) -> None:
        """Атомарно записывает данные в файл кеша."""
        self._atomic_write(self.config.RATES_FILE_PATH, cache)

    def _atomic_write(self, file_path: Path, data: any) -> None:
        """Выполняет атомарную запись в JSON файл."""
        temp_file = file_path.with_suffix(f"{file_path.suffix}.tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_file.replace(file_path)
        except Exception as e:
            logger.error(f"Failed to write to {file_path}: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise




