from typing import Dict, Any, Optional, Callable, Coroutine
from functools import wraps
from telethon import events


class FSM:
    def __init__(self):
        self.states: Dict[int, str] = {}  # user_id -> state
        self.data: Dict[int, Dict[str, Any]] = {}  # user_id -> data dict

    def get_state(self, user_id: int) -> Optional[str]:
        return self.states.get(user_id)

    def set_state(self, user_id: int, state: str):
        self.states[user_id] = state

    def reset_state(self, user_id: int):
        if user_id in self.states:
            del self.states[user_id]
        if user_id in self.data:
            del self.data[user_id]

    def get_data(self, user_id: int) -> Dict[str, Any]:
        if user_id not in self.data:
            self.data[user_id] = {}
        return self.data[user_id]

    def update_data(self, user_id: int, **kwargs):
        data = self.get_data(user_id)
        data.update(kwargs)

    def handler(self, state: str):
        """Декоратор для хендлеров, срабатывающих только в определённом состоянии."""
        def decorator(func: Callable[[events.NewMessage.Event], Coroutine]):
            @wraps(func)
            async def wrapper(event: events.NewMessage.Event):
                current_state = self.get_state(event.sender_id)
                if current_state == state:
                    return await func(event)
            return wrapper
        return decorator

    def no_state_handler(self):
        """Декоратор для обработки сообщений, когда у пользователя НЕТ состояния."""
        def decorator(func):
            @wraps(func)
            async def wrapper(event):
                current_state = self.get_state(event.sender_id)
                if current_state is None:  # проверяем именно на None (не False)
                    return await func(event)
            return wrapper
        return decorator


fsm_obj = FSM()
