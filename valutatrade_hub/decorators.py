"""
Декораторы для логирования и аудита операций.

Содержит декоратор @log_action для прозрачной трассировки
ключевых бизнес-операций (buy, sell, register, login).
"""
import functools
import logging
from datetime import datetime
from typing import Any, Callable

# Настройка логгера для декоратора
logger = logging.getLogger("valutatrade.actions")


def log_action(
    action_type: str,
    verbose: bool = False
) -> Callable:
    """
    Декоратор для логирования доменных операций.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            user_id = kwargs.get('user_id') or (args[1] if len(args) > 1 else None)
            currency = kwargs.get('currency') or (args[2] if len(args) > 2 else None)
            amount = kwargs.get('amount') or (args[3] if len(args) > 3 else None)
            
            username = kwargs.get('username') or (
                args[1] if len(args) > 1 and action_type in ['REGISTER', 'LOGIN'] 
                else None
            )
            
            timestamp = datetime.now().isoformat()
            
            try:
                result = func(*args, **kwargs)
                
                if action_type in ['BUY', 'SELL']:
                    if isinstance(result, dict):
                        rate = result.get('rate', 'N/A')
                    else:
                        rate = 'N/A'
                    
                    log_msg = (
                        f"{timestamp} {action_type} "
                        f"user_id={user_id} currency='{currency}' "
                        f"amount={amount:.4f} rate={rate} base='USD' result=OK"
                    )
                    
                    if verbose and isinstance(result, dict):
                        old_balance = result.get('old_balance', 'N/A')
                        new_balance = result.get('new_balance', 'N/A')
                        log_msg += (
                            f" | balance_change: "
                            f"{old_balance:.4f} -> {new_balance:.4f}"
                        )
                
                elif action_type == 'REGISTER':
                    log_msg = (
                        f"{timestamp} {action_type} "
                        f"username='{username}' result=OK"
                    )
                    if verbose and isinstance(result, object):
                        user_id = getattr(result, 'user_id', 'N/A')
                        log_msg += f" | new_user_id={user_id}"
                
                elif action_type == 'LOGIN':
                    log_msg = (
                        f"{timestamp} {action_type} "
                        f"username='{username}' result=OK"
                    )
                    if verbose and isinstance(result, object):
                        user_id = getattr(result, 'user_id', 'N/A')
                        log_msg += f" | user_id={user_id}"
                else:
                    log_msg = f"{timestamp} {action_type} result=OK"
                
                logger.info(log_msg)
                return result
            
            except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)
                
                log_parts = [
                    f"{timestamp} {action_type}",
                    f"user_id={user_id}" if user_id else f"username='{username}'",
                    f"currency='{currency}'" if currency else "",
                    f"amount={amount}" if amount is not None else "",
                    "result=ERROR",
                    f"error_type={error_type}",
                    f"error_message='{error_message}'"
                ]
                log_msg = " ".join(part for part in log_parts if part)
                
                logger.error(log_msg)
                raise
        
        return wrapper
    return decorator

