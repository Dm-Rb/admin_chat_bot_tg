from telethon import TelegramClient
from config import config
from admin_handler import GroupWipeHandler


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
        self._register_handlers()

    def _register_handlers(self):
        handlers = [
            GroupWipeHandler
        ]

        for handler in handlers:
            handler.register(self.client)

    async def start(self):
        await self.client.start(phone=self.phone)
        await self.client.run_until_disconnected()


if __name__ == '__main__':
    bot = TelegramBot()
    print('> run bot')
    bot.client.loop.run_until_complete(bot.start())
