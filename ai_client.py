from config import config
import aiohttp
from log import logger


class DeepSeekAPIClient:

    LIMIT_HISTORY = 40

    def __init__(self, token):
        self.API_BASE_URL = 'https://api.deepseek.com'
        self.API_ENDPOINT = '/chat/completions'
        self.API_BALANCE = '/user/balance'
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {str(token)}"
            }
        self._session = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Lazy initialization of session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(base_url=self.API_BASE_URL)  # ! ONLY API_BASE_URL
        return self._session

    async def close(self):
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
                "temperature": config.ai_temperature,
                "messages": messages_history,
                "stream": False
            }
            # url Only endpoint (session add base_url)
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

    async def request_get_balance(self):
        session = await self.get_session()
        try:
            async with session.get(self.API_BALANCE, headers=self.headers) as resp:
                resp.raise_for_status()  # Проверяем статус ответа
                response_json = await resp.json()
                for item in response_json['balance_infos']:
                    return f"{item['total_balance']} {item['currency']}"
        except Exception as e:
            logger.error(
                f"f.request_post error: {e}\n",
                exc_info=True)
            raise e


deep_seek = DeepSeekAPIClient(config.ai_token)
