from telethon import events
from telethon.tl.functions.messages import DeleteMessagesRequest
from ai_client import deep_seek
from fsm import fsm_obj
import re


class States:
    waiting_role_state = "waiting_role"


class AiChatHandler(States):

    LIMIT_HISTORY = 40
    my_tg_id = None
    my_tg_username = None
    my_tg_first_name = None
    roles = {}  # {chat_id/user_id: str, chat_id/user_id: str, ...}
    cmd_set_role = "/set_role"
    cmd_get_balance = "/get_balance"
    cmd_wipe_history = "/wipe_history"
    prefix = "O, kurwa"

    @classmethod
    def register(cls, client) -> None:

        # Handler for new message in private chat
        @client.on(events.NewMessage(func=lambda e: e.is_private and cls.is_not_cmd(e.text)))
        @fsm_obj.no_state_handler()
        async def message_handler_private_chat(event):
            await cls.message_handler(event, client)

        # Handler for new message in group chat
        @client.on(events.NewMessage(func=lambda e: e.is_group))
        @fsm_obj.no_state_handler()
        async def message_handler_group_chat(event):
            if (event.is_reply and (await event.get_reply_message()).sender_id == (await client.get_me()).id) or \
            (cls.my_tg_username and (cls.my_tg_username in event.text)) or \
            (cls.my_tg_first_name and (event.text.lower().startswith(cls.my_tg_first_name.lower()))):
                await cls.message_handler(event, client)

        # Handler for command <cmd_set_role> in any chat
        @client.on(events.NewMessage(pattern=cls.cmd_set_role))
        async def set_role_command(event):
            # Initializing the state
            fsm_obj.set_state(chat_id=event.chat_id, state=cls.waiting_role_state)
            # Add the ID of the user who performed the initialization to the FSM state
            fsm_obj.update_data(chat_id=event.chat_id, user_id=event.sender_id)
            return await event.respond("Send a text description of the AI role to the chat 👇🏻")

        # Handler for state <States.waiting_role_state> in any chat
        @client.on(events.NewMessage(func=lambda e: not cls.is_not_cmd(e.text)))
        @fsm_obj.handler(cls.waiting_role_state)
        async def install_new_role_2_model(event):
            user_id_from_fsm = fsm_obj.get_data(event.chat_id)  # Get sender id from fsm

            # If the bot sent a message to itself in the chat (excluding cases where it’s responding to a user request)
            if int(event.sender_id) != int(user_id_from_fsm['user_id']):
                return
            role = event.text.strip()
            cls.roles[event.chat_id] = role
            fsm_obj.reset_state(chat_id=event.chat_id)
            return await event.respond("✅ New role installed")

        # Handler for command <cmd_get_balance> in any chat
        @client.on(events.NewMessage(pattern=cls.cmd_get_balance))
        async def set_role_command(event):
            try:
                balance = await deep_seek.request_get_balance()
                return await event.respond(balance)
            except Exception as _ex:
                return await event.respond(cls.prefix + f"‼️ <set_role_command> Error: {_ex}")

        # Handler for command <cmd_wipe_history> in any chat
        @client.on(events.NewMessage(pattern=cls.cmd_wipe_history))
        async def set_role_command(event):
            try:
                r = await cls.wipe_chat_history(event)
                if r:
                    return await event.respond("✅ The messages have been deleted")
                else:
                    return await event.respond("👌🏻")
            except Exception as _ex:
                return await event.respond(cls.prefix + f"‼️ <set_role_command> Error: {_ex}")

    @classmethod
    async def message_handler(cls, event, client) -> None:

        if int(event.sender_id) == cls.my_tg_id:
            return

        if event.message.media is not None:
            return await event.respond("❕ The DeepSeek API does not support file uploads at this time.")

        ai_role = cls.roles.get(event.chat_id, None)
        try:
            ai_chat_history = await cls.get_ai_chat_history(client, event.chat_id, ai_role)
        except Exception as _ex:
            return await event.respond(cls.prefix + f"‼️ <get_ai_chat_history> Error: {_ex}")

        async with client.action(event.chat_id, 'typing'):
            try:
                ai_client_response = await deep_seek.request_post(ai_chat_history, ai_role, str(event.text))
                ai_client_response = cls.replace_diez_in_text(ai_client_response)
                return await event.respond(ai_client_response, parse_mode="markdown", reply_to=event.message.id)
            except Exception as ex_:
                return await event.respond(cls.prefix + f"‼️ Request Error: {ex_}")

    @classmethod
    async def get_ai_chat_history(cls, client, chat_id, ai_role=None) -> list[dict]:
        """
        This method creates an array containing the history of user requests and corresponding AI responses.
        Messages are extracted from the specified Telegram chat passed as an argument.
        Messages unrelated to the user-AI dialogue (such as user commands or system messages from the bot) are ignored.
        The filtering mechanism works by relying on the fact that AI responses to the user always include message
        quoting (<reply_to_msg>). User requests and AI responses form logical pairs since every AI reply object
        contains the <reply_to_msg_id> attribute. Method returns a list of dictionaries.
        """

        ai_chat_history = []  # result list
        # <user_messages> contains message texts and IDs for all messages sent by any users except this bot
        # (this Telegram account)
        user_messages = {}  # {int(message_id): str(message_text), ...}
        # <bot_messages> contains message texts and reply message IDs
        bot_messages = []  # [{'message': str(message_text), 'reply_to_msg_id': int(reply_to_msg_id)}, {...}, ...]

        # "Retrieve all messages from the specified chat and sort them into <bot_messages> and <user_messages>
        async for message in client.iter_messages(chat_id):
            msg_id = message.id
            msg_sender_id = message.sender_id
            reply_to_msg_id = message.reply_to_msg_id
            if msg_sender_id == cls.my_tg_id:
                bot_messages.append({'message': message.text, 'reply_to_msg_id': reply_to_msg_id})
            else:
                user_messages[msg_id] = {'message': message.text}

        # Reverse the list to place oldest messages first and newest last
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
            
        default_role = f'{f"Твае імя - {cls.my_tg_first_name}. " if cls.my_tg_first_name else ""}' + \
                       f'Ты карысны памочнік. У адказах заўсёды карыстайся беларускай мовай'

        role_item = {"role": "system", "content": default_role if not ai_role else ai_role}
        return [role_item] + ai_chat_history

    @staticmethod
    def replace_diez_in_text(text) -> str:
        try:
            result = re.sub(r'#{3,4}', '✳️', text)
            return result
        except (re.error, TypeError) as e:
            return text

    @classmethod
    def is_not_cmd(cls, message_text) -> bool:
        # True - if message_text is not command
        cmd_list = [cls.cmd_set_role, cls.cmd_get_balance, cls.cmd_wipe_history]
        return not any(message_text.startswith(cmd) for cmd in cmd_list)

    @classmethod
    async def wipe_chat_history(cls, event) -> bool:
        """Deletes all its messages in the chat"""

        flag = False
        ids_message_of_bot = []
        # Filters out the message IDs that the bot sent in the chat
        async for message in event.client.iter_messages(event.chat_id):
            if message.sender_id == cls.my_tg_id:
                ids_message_of_bot.append(message.id)

        # Only up to 100 messages can be deleted in one go; this is a Telegram restriction
        step = 100
        for i in range(0, len(ids_message_of_bot), step):
            chunk_message_ids = ids_message_of_bot[i:i + step]

            # Removes a batch of messages specified by message IDs
            await event.client(DeleteMessagesRequest(
                id=chunk_message_ids,
                revoke=True
            ))
            flag = True
        return flag



