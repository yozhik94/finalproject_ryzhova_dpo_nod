#!/usr/bin/env python
"""
Главная точка входа приложения Currency Wallet.

Запуск команд:
    python main.py register --username alice --password 123
    python main.py sell --currency BTC --amount 0.5
    python main.py update-rates
    python main.py update-rates --source coingecko
    python main.py show-rates
    python main.py show-rates --currency BTC
    python main.py show-rates --top 2
"""
from valutatrade_hub.cli.interface import main

if __name__ == "__main__":
    main()
