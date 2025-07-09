from config import config
import aiohttp
from log import logger


class DeepSeekAPIClient:

    LIMIT_HISTORY = 40
    temperature = 0.70

    def __init__(self, token):
        self.API_BASE_URL = 'https://api.deepseek.com'
        self.API_ENDPOINT = '/chat/completions'  # Эндпоинт отдельно
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {str(token)}"
            }
        self._session = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Ленивая инициализация сессии"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(base_url=self.API_BASE_URL)  # Используем только базовый URL
        return self._session

    async def close(self):
        """Явное закрытие сессии"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def request_post(self, messages_history: list, ai_role: str, user_request: str):
        try:
            session = await self.get_session()
            if not messages_history:
                messages_history = [
                    {"role": "system", "content": "You are a helpful assistant." if not ai_role else ai_role},
                    {"role": "user", "content": user_request}
                ]
            else:
                messages_history.append(
                    {"role": "user", "content": user_request}
                )
            body_ = {
                "model": "deepseek-chat",
                "temperature": self.temperature,
                "messages": messages_history,
                "stream": False
            }
            # url Только эндпоинт (сессия добавит base_url)
            async with session.post(self.API_ENDPOINT, json=body_, headers=self.headers) as resp:
                resp.raise_for_status()  # Проверяем статус ответа
                response_json = await resp.json()

                if not response_json.get('choices', None):
                    raise ValueError("The API response does not contain the 'choices' key")
                for choice_item in response_json['choices']:
                    return choice_item['message']['content']
        except Exception as e:
            logger.error(
                f"f.request_post error: {e}\n",
                exc_info=True)
            raise e

deep_seek = DeepSeekAPIClient(config.ai_token)
