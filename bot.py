from telethon import TelegramClient
from config import config
from pathlib import Path
from ai_chat_bot import AiChatHandler


"""
telethon documentation
https://docs.telethon.dev/en/stable/basic/quick-start.html
"""


class TelegramBot:
    def __init__(self):
        self.api_id = config.api_id
        self.api_hash = config.api_hash
        self.phone = config.phone_number
        self.client = TelegramClient('session_name', self.api_id, self.api_hash)
        self.my_id = None
        self.my_username = None
        self.my_first_name = None
        self.handlers = [
            AiChatHandler
        ]
        self._register_handlers()
        # Folder for files
        # Path(config.folder_4_json).mkdir(parents=True, exist_ok=True)

    def _register_handlers(self):

        for handler in self.handlers:
            handler.register(self.client)

    def _set_attr_handlers(self):
        for handler in self.handlers:
            if hasattr(handler, 'my_tg_id'):
                handler.my_tg_id = self.my_id
            if hasattr(handler, 'my_tg_username'):
                handler.my_tg_username = self.my_username
            if hasattr(handler, 'my_tg_first_name'):
                handler.my_tg_first_name = self.my_first_name

    async def start(self):
        await self.client.start(phone=self.phone)
        # Get info about tg account
        me = await self.client.get_me()
        self.my_id = me.id
        self.my_username = me.username
        self.my_first_name = me.first_name
        # Set info into handlers
        self._set_attr_handlers()

        await self.client.run_until_disconnected()


if __name__ == '__main__':
    bot = TelegramBot()
    print('> run bot')
    bot.client.loop.run_until_complete(bot.start())
