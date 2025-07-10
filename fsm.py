from typing import Dict, Any, Optional, Callable, Coroutine
from functools import wraps
from telethon import events


class FSM:
    def __init__(self):
        self.states: Dict[int, str] = {}  # chat_id -> state
        self.data: Dict[int, Dict[str, Any]] = {}  # user_id -> data dict

    def get_state(self, chat_id: int) -> Optional[str]:
        return self.states.get(chat_id)

    def set_state(self, chat_id: int, state: str):
        self.states[chat_id] = state

    def reset_state(self, chat_id: int):
        if chat_id in self.states:
            del self.states[chat_id]
        if chat_id in self.data:
            del self.data[chat_id]

    def get_data(self, chat_id: int) -> Dict[str, Any]:
        if chat_id not in self.data:
            self.data[chat_id] = {}
        return self.data[chat_id]

    def update_data(self, chat_id: int, **kwargs):
        data = self.get_data(chat_id)
        data.update(kwargs)

    def handler(self, state: str):
        """Декоратор для хендлеров, срабатывающих только в определённом состоянии."""
        def decorator(func: Callable[[events.NewMessage.Event], Coroutine]):
            @wraps(func)
            async def wrapper(event: events.NewMessage.Event):
                current_state = self.get_state(event.chat_id)
                if current_state == state:
                    return await func(event)
            return wrapper
        return decorator

    def no_state_handler(self):
        """Декоратор для обработки сообщений, когда у пользователя НЕТ состояния."""
        def decorator(func):
            @wraps(func)
            async def wrapper(event):
                current_state = self.get_state(event.chat_id)
                if current_state is None:  # проверяем именно на None (не False)
                    return await func(event)
            return wrapper
        return decorator


fsm_obj = FSM()
