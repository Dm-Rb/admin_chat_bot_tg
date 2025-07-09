from telethon import events
from ai_client import deep_seek
from fsm import fsm_obj


# Определяем состояния
class States:
    waiting_role = "waiting_role"


class AiChatHandler:

    LIMIT_HISTORY = 40
    my_tg_id = None
    roles = {}  # {chat_id/user_id: str, chat_id/user_id: str, ...}
    cmd_set_role = "/set_role"
    
    @classmethod
    def register(cls, client) -> None:

        @client.on(events.NewMessage(func=lambda e: e.is_private and not e.text.startswith(cls.cmd_set_role)))  # Filter
        @fsm_obj.no_state_handler()
        async def _message_handler(event):
            sender = await event.get_sender()

            if event.message.media is not None:
                return await event.respond("The DeepSeek API does not support file uploads at this time.")                

            ai_role = cls.roles.get(event.chat_id, None)
            ai_chat_history = await cls.get_ai_chat_history(client, sender.id, ai_role)
            async with client.action(event.chat_id, 'typing'):
                try:
                    ai_response = await deep_seek.request_post(ai_chat_history, ai_role, str(event.text))
                    return await event.respond(ai_response, parse_mode="markdown", reply_to=event.message.id)
                except Exception as ex_:
                    return await event.respond(f"‼️ Request Error: {ex_}")

        @client.on(events.NewMessage(pattern=cls.cmd_set_role))
        async def set_role_command(event):
            fsm_obj.set_state(user_id=event.sender_id, state=States.waiting_role)
            return await event.respond("Send a text description of the AI role to the chat.")

        @client.on(events.NewMessage(func=lambda e: e.is_private and not e.text.startswith(cls.cmd_set_role)))  # Filter
        @fsm_obj.handler(States.waiting_role)
        async def install_new_role_2_model(event):
            sender = await event.get_sender()
            role = event.text.strip()
            cls.roles[sender.id] = role
            fsm_obj.reset_state(user_id=sender.id)
            return await event.respond("New role installed")            

    @classmethod
    async def get_ai_chat_history(cls, client, chat_id, ai_role=None):
        user_messages = {}
        bot_messages = []
        ai_chat_history = []
        role_item = {"role": "system", "content": "You are a helpful assistant." if not ai_role else ai_role}
        async for message in client.iter_messages(chat_id):
            sender = await message.get_sender()
            if sender.id == cls.my_tg_id:
                bot_messages.append({'message': message.text, 'reply_to_msg_id': message.reply_to_msg_id})
            else:
                user_messages[message.id] = {'message': message.text}
        bot_messages.reverse()
        for bot_item in bot_messages:
            if not bot_item.get('reply_to_msg_id', None):
                continue
            bot_message = bot_item['message']
            reply_msg_id = bot_item['reply_to_msg_id']
            user_message = user_messages[reply_msg_id]['message']
            ai_chat_history.append({"role": "user", "content": user_message})
            ai_chat_history.append({"role": "assistant", "content": str(bot_message)})
        if len(ai_chat_history) > cls.LIMIT_HISTORY:
            ai_chat_history = ai_chat_history[len(ai_chat_history) - cls.LIMIT_HISTORY:]
        return [role_item].extend(ai_chat_history)



