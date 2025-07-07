from telethon import events
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
from telethon.errors import ChatAdminRequiredError, MessageDeleteForbiddenError, MessageIdsEmptyError
import asyncio
from config import config
import datetime
import os
from log import logger
import json



"""
telethon documentation
https://docs.telethon.dev/en/stable/basic/updates.html
"""


class GroupWipeHandlerMessages:
    """
    This class contains text and functions for generating text messages.
    It is the parent class for <GroupWipeHandler>.
    It does not contain any logic related to the <telethon> module, only text processing.
    """

    cmd_total_wipe = '/wipe_total'
    cmd_personal_wipe = '/wipe_myself'
    cmd_help = '/help'
    cmd_import_history = '/import_history'
    msg_run_global_wipe = "❕ Запускаю глабальны вайп УСІХ паведамленняў у гэтай групе. "
    msg_run_personal_wipe = "❕ Запускаю вайп АСАБІСТАЙ гісторыі паведамленняў удзельніка гэтай групы"
    msg_permission_denied = "❗️ Неабходны права администатора для выканання дадзенай працэдуры [*права на выдаленне паведамленняў*]"
    msg_help = "✳️ Для выдалення ЎСІХ паведамленняў адпраўце ў чат:\n" + \
               f"<code>{cmd_total_wipe}</code>\n" + \
               f"<i>[патрабуецца {str(config.total_wipe_confirms)} запыт(а) ад розных удзельнікаў групы на працягу 24 гадзін]</i>\n\n" + \
               "✳️ Для выдалення СВАІХ асабістых паведамленняў адпраўце ў чат:\n" + \
               f"<code>{cmd_personal_wipe}</code>\n\n" + \
               "🔄 Праз 24 гадзіны ўсе запыты ад карыстальнікаў скідваюцца.\n\n" + \
               "✳️ Для атрымання спраўкі адпраўце ў чат:\n" + \
               f"<code>{cmd_help}</code>"

    msg_about_bot = '<b>Вітанкі!</b>\n' \
                    'Гэты бот створаны для хуткага выдалення ўсей гісторыі паведамленнаў ' \
                    'гэтага групавога чата по запыту ўдзельнікаў.\n' + \
                    'Так сама маецца опцыя выдалення сваіх асабістых паведамленняў у гэтай групе.\n\n' + \
                    '❕ Для карэктнай працы неабходна выдаць боту правы адміністратара.\n\n' \
                    '❕ Так сама калі група змяшчае болей 100 паведамленняў, неабходна адчыныць усю гісторыю паведамленняў.\n\n' \
                    'Для гэтага  неабходна зайсці ў пункт меню ⚙️ <i>"Кіраванне групай"</i>.\n' + \
                    'Далей знайсци опцыю ⚙️ <i>"Гисторыя чата для новых удзельнікаў"</i> и выставіць  чэкбокс на <i>"Бачна"</i>\n\n'
    msg_import_history = 'Адпраўце боту файл <b>result.json</b>, які змяшчае гісторыю паведамленняў гэтага группавога чата.\n' \
                         'Для атрымання файла <b>result.json</b> націсніце на тры кропкі ў верхнем правым вуглу.\n<b>1.</b> Далей абярыце ' \
                         '⚙️ <i>Экспартаваць гісторыю"</i>.\n<b>2.</b> У адчыніўшымся акне знайдзіце поле <i>Фармат</i> і націсніце ' \
                         'на <i>HTML</i>, што побач.\n<b>3.</b> Змяніце фармат з <i>HTML</i> на <i>JSON</i> і захавайце змены.\n<b>4.</b> Націсніце на кнопку' \
                         ' 👉🏻 <i>"Імпартаваць"</i>. Тэлеграм сфарміруе файл і пачне спампоўваць яго на вашу прыладу.\n' \
                         '<b>5.</b> Пасля заканчэння спампоўкі націсніце на кнопку 👉🏻 <i>"Паказаць даныя"</i>. Вас пераадрасуе па шляху ' \
                         'захавання файла <b>result.json</b>.<b>\n6.</b> Адпраўце гэты файл сюды ў чат 📤' \

    msg_complete = "✅ Зроблена"

    msg_import_history_complete = "Імпартр гісторыі паведамленняў выкананы"

    @staticmethod
    def _msg_confirm_total_wipe(user_requests, lack_of_requests):
        msg = \
            f"{str(user_requests)} пользователь(я) " + \
            f"запросил(и) глобальный вайп сообщений в данном групповом чате в течении последних суток.\n" + \
            f"\nНеобходимо ещё {str(lack_of_requests)} " + \
            f"запрос(а) для запуска процедуры очистки..."
        return msg

    @classmethod
    def _msg_confirm_personal_wipe(cls, user_name, necessary_requests):
        msg = \
            f"{user_name}, Вы запросили удаление всей истории собственных сообщений в текущем групповом чате.\n\n" + \
            f"Для запуска процедуры очистки отправьте команду {cls.cmd_personal_wipe} " \
            f"ещё {str(necessary_requests)} раз(а) для подтверждения."
        return msg


class GroupWipeHandler(GroupWipeHandlerMessages):
    """
    This class is integrated into the main module upon initialization of the TelegramBot class instance.
    It contains the logic for interacting with messages in Telegram group chats (message deletion).
    It inherits from the <GroupWipeHandlerMessages> class, which handles text content.
    Message interaction logic is triggered when users send specific commands in the group chat
    (GroupWipeHandlerMessages.cmd_total_wipe, GroupWipeHandlerMessages.cmd_personal_wipe, etc.).
    The main method, async def message_handler, monitors all user messages in the group chat (via a filter).
    If a message contains one of the specified commands, it triggers the corresponding handler.
    To activate the handler (message deletion), the command must be sent multiple times
    (the exact count is defined in the config file).
    This prevents false triggers. The command counter resets after 24 hours.
    """

    # This attribute contains the request objects for mass message deletion in chats
    total_wipe_requests = {}  # {chat_id: {user_id: date_time, user_id: date_time, ..}, chat_id: {...}, ...}

    # This attribute stores request objects for per-user message deletion in chats
    personal_wipe_requests = {}  # {chat_id: {user_id: [date_time, date_time], user_id: [...], ...}, chat_id: {...} ...}

    @classmethod
    def register(cls, client) -> None:
        """
        Main method that manages message processing handlers.
        Connected during <TelegramBot> class initialization
        through the <_register_handlers> function in <bot.py>.
        """

        # Handles the workflow when bot is added to a new group
        @client.on(events.ChatAction())  # Фильтр
        async def chat_action_handler(event):
            if event.user_added and event.is_channel:
                # Sends a welcome message with bot usage instructions to the chat
                await event.respond(cls.msg_about_bot + cls.msg_help, parse_mode='html')

        #  Message handler for group chats. Processes all group messages and looks for commands
        #  (GroupWipeHandlerMessages.cmd_total_wipe, GroupWipeHandlerMessages.cmd_personal_wipe, etc.)
        @client.on(events.NewMessage(func=lambda e: e.is_group))  # Filter
        async def _message_handler(event):
            event_text_split: list = event.text.split()  # Extract and split message content
            if not event.text:  # If the message object contains no letters
                return
            # Check if the full group wipe command exists in <event_text_split>
            if cls.cmd_total_wipe in event_text_split:
                # Checks if bot has admin rights in this group
                if not await cls._is_bot_admin(event):
                    # Sends a message that the bot requires admin privileges
                    await event.respond(cls.msg_permission_denied)
                    return
                # Checks if enough user requests accumulated for message purge
                # Threshold configurable in settings
                confirm: bool = await cls._confirm_total_wipe(event)
                if confirm:
                    # # Deletes ALL messages from ALL users in the group chat
                    await cls._total_wipe_messages(event)
                    return
                else:
                    return
            # The command to delete a USER'S message history within the group is contained in <event_text_split>
            elif cls.cmd_personal_wipe in event_text_split:
                # Checks if bot has admin rights in this group
                if not await cls._is_bot_admin(event):
                    # Sends a message that the bot requires admin privileges
                    await event.respond(cls.msg_permission_denied)
                    return
                # Verifies if enough user requests exist to trigger message deletion
                # (Multiple confirmations required to prevent false positives; threshold set in config)
                confirm: bool = await cls._confirm_personal_wipe(event)
                if confirm:
                    # Deletes all messages from a specific group member (who initiated the deletion command)
                    await cls._personal_wipe_messages(event)
                    return
                else:
                    return
            # If the help command is present in <event_text_split>
            elif cls.cmd_help in event_text_split:
                # Send help message
                await event.respond(cls.msg_help, parse_mode='html')
                return
            elif cls.cmd_import_history in event_text_split:
                # Send message
                photos = [os.path.join('images', i)for i in ('1.png', '2.png', '3.png', '4.png', '5.png', '6.png')]
                await client.send_file(
                    event.chat_id,
                    photos,
                    caption=cls.msg_import_history,
                    as_album=True,
                    parse_mode='HTML'
                )
                return
            else:
                return

        @client.on(events.NewMessage(
            func=lambda e: e.is_group and cls.is_json_file(e)
        )
        )
        async def json_file_handler(event):
            file_bytes = await event.download_media(file=bytes)
            try:
                data = json.loads(file_bytes.decode('utf-8'))
            except Exception as ex_:
                return
            if not cls.validate_json_structure(data, event.chat_id):
                return
            await event.download_media(file=os.path.join(config.folder_4_json, f"{event.chat_id}.json"))
            await event.reply(cls.msg_import_history_complete)

    @classmethod
    async def _is_bot_admin(cls, event) -> bool:
        """
        Verifies whether the bot is a group administrator with message deletion privileges.
        """

        try:
            # Getting information about yourself <https://docs.telethon.dev/en/stable/basic/quick-start.html>
            me = await event.client.get_me()

            # Getting information about chat
            chat = await event.get_chat()

            # For supergroups/channels
            if hasattr(chat, 'admin_rights'):
                # Verify bot's access rights
                if chat.admin_rights and chat.admin_rights.delete_messages:
                    return True
            # Retrieve full permission details
            try:
                permissions = await event.client.get_permissions(chat.id, me.id)

                # Validate admin permissions
                if isinstance(permissions.participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
                    # Verify the right to delete messages
                    if isinstance(permissions.participant, ChannelParticipantCreator):
                        return True
                    if isinstance(permissions.participant, ChannelParticipantAdmin):
                        return permissions.participant.admin_rights.delete_messages
            except ChatAdminRequiredError as e:
                logger.error(
                    f"ChatAdminRequiredError: {str(e)}\n",
                    exc_info=True)
                pass
            return False

        except Exception as e:
            logger.error(
                f"Failed to verify administrator rights: {str(e)}\n",
                exc_info=True)
            return False

    @classmethod
    async def _confirm_total_wipe(cls, event) -> bool:
        """
        Determines if all necessary conditions exist to perform a global wipe.
        """

        # # Records current time for comparison with datetime objects in <total_wipe_requests>
        datetime_now = datetime.datetime.now()
        # Retrieves chat id info and message sender's user id
        sender = await event.get_sender()
        chat_id = event.chat_id
        user_id = sender.id

        # If command sender's ID is already recorded in <cls.total_wipe_requests>
        # -> iterating to objects
        if cls.total_wipe_requests.get(chat_id, None):
            for key, value in cls.total_wipe_requests[chat_id].items():
                # key - user_id, value - datetime.now object
                time_difference = abs(datetime_now - value)
                # Clear dict if any item ->24h old (daily counter reset)
                if not time_difference < datetime.timedelta(days=1):
                    cls.total_wipe_requests[chat_id].clear()
                    break
            # Adds {user_id: datetime_now} pair to <total_wipe_requests>
            cls.total_wipe_requests[chat_id][user_id] = datetime_now
            # If the required number of wipe requests from users has been reached
            if len(cls.total_wipe_requests[chat_id].keys()) >= config.total_wipe_confirms:
                # Clear dict and return True
                cls.total_wipe_requests[chat_id].clear()
                await event.respond(cls.msg_run_global_wipe)
                return True
            else:
                # Sends notification to group chat about insufficient wipe requests
                await event.respond(cls._msg_confirm_total_wipe(
                    len((cls.total_wipe_requests[chat_id].keys())),
                    config.total_wipe_confirms - len(cls.total_wipe_requests[chat_id].keys()))
                )
                return False
        else:
            # When the user ID isn't found in <cls.total_wipe_requests> keys
            # -> create new tracking record in the dictionary
            cls.total_wipe_requests[chat_id] = {}
            cls.total_wipe_requests[chat_id][user_id] = datetime_now

            await event.respond(cls._msg_confirm_total_wipe(
                len((cls.total_wipe_requests[chat_id].keys())),
                config.total_wipe_confirms - len(cls.total_wipe_requests[chat_id].keys()))
            )
            return False

    @classmethod
    async def _delete_batch_messages(cls, event, message_ids: list[int]):
        from telethon.tl.functions.messages import DeleteMessagesRequest
        if len(message_ids) > 100:
            logger.error("It's impossible to delete more than 100 messages at a time")
            await event.respond('Delete error')
            return

        # try:
        chat_id = event.chat_id if str(event.chat_id).startswith('-100') else f'-100{abs(event.chat_id)}'
            # print(chat_id)
        await event.client(DeleteMessagesRequest(
            id=message_ids,
            revoke=True  # Удалить у всех (если есть права)
        ))

        await event.client.delete_messages(int(chat_id), message_ids, revoke=True)
        # except Exception as e:
        #     await event.respond('Delete error')
        #     logger.error(f"Delete error: {str(e)}")

    @classmethod
    async def _total_wipe_messages(cls, event):
        """Method for complete group chat message purge."""
        execution_status: list[bool] = []
        try:
            if os.path.exists(os.path.join(config.folder_4_json, f"{event.chat_id}.json")):
                with open(os.path.join(config.folder_4_json, f"{event.chat_id}.json"), 'r', encoding='utf-8') as f:
                    exported_messages = json.load(f)
                step = 100
                for i in range(0, len(exported_messages['messages']), step):
                    chunk_message_ids = [i['id'] for i in exported_messages['messages'][i:i + step]]
                    await cls._delete_batch_messages(event, chunk_message_ids)
                    await asyncio.sleep(0.5)
                execution_status.append(True)
                # os.remove(os.path.join(config.folder_4_json, f"{event.chat_id}.json"))
        except Exception as ex_:
            execution_status.append(False)
            logger.error(f"Error when trying to remove messages from the export file: {str(ex_)}", exc_info=True)

        try:
            message_ids = []
            async for message in event.client.iter_messages(event.chat_id, limit=None):  # None = all messages
                message_ids.append(message.id)
            step = 100
            for i in range(0, len(message_ids), step):
                chunk_message_ids = message_ids[i:i + step]
                await cls._delete_batch_messages(event, chunk_message_ids)
                await asyncio.sleep(0.5)
            execution_status.append(True)
        except Exception as ex_:
            execution_status.append(False)
            logger.error(f"Error when trying to remove messages: {str(ex_)}", exc_info=True)

        # if any(execution_status):
        #     await event.reply(
        #         cls.msg_complete,
        #         file=os.path.join('images', 'pepe.png')
        #     )
        # else:
        #     await event.respond('❌ Failed to delete messages ❌')

    @classmethod
    async def _confirm_personal_wipe(cls, event) -> bool:
        """
        Determines if all necessary conditions exist to perform to wipe user's messages in chat.
        """

        # Records current time for comparison with datetime objects in <total_wipe_requests>
        datetime_now = datetime.datetime.now()
        sender = await event.get_sender()
        chat_id = event.chat_id
        user_id = sender.id
        first_name = sender.first_name
        last_name = getattr(sender, 'last_name', None)
        full_name = f"{first_name} {last_name}" if last_name else first_name

        if cls.personal_wipe_requests.get(chat_id, None):
            # If chat_id exist in  cls.personal_wipe_requests -> iterate to list[datetime, ...]
            if cls.personal_wipe_requests[chat_id].get(user_id, None):
                if len(cls.personal_wipe_requests[chat_id][user_id]) > 0:
                    for datetime_item in cls.personal_wipe_requests[chat_id][user_id]:
                        time_difference = abs(datetime_now - datetime_item)
                        if not time_difference < datetime.timedelta(days=1):
                            cls.personal_wipe_requests[chat_id][user_id].clear()
                            break

                    cls.personal_wipe_requests[chat_id][user_id].append(datetime_now)
                    if len(cls.personal_wipe_requests[chat_id][user_id]) >= config.personal_wipe_confirms:
                        cls.personal_wipe_requests[chat_id][user_id].clear()
                        await event.respond(f'{cls.msg_run_personal_wipe}\n{full_name}')
                        return True
                    else:
                        necessary_requests = \
                            config.personal_wipe_confirms - len(cls.personal_wipe_requests[chat_id][user_id])
                        await event.respond(cls._msg_confirm_personal_wipe(full_name, necessary_requests))
                        return False
                else:
                    cls.personal_wipe_requests[chat_id][user_id].append(datetime_now)
                    necessary_requests = \
                        config.personal_wipe_confirms - len(cls.personal_wipe_requests[chat_id][user_id])
                    await event.respond(cls._msg_confirm_personal_wipe(full_name, necessary_requests))
                    return False
            else:
                cls.personal_wipe_requests[chat_id][user_id] = []
                cls.personal_wipe_requests[chat_id][user_id].append(datetime_now)
                necessary_requests = \
                    config.personal_wipe_confirms - len(cls.personal_wipe_requests[chat_id][user_id])
                await event.respond(cls._msg_confirm_personal_wipe(full_name, necessary_requests))
                return False
        else:
            cls.personal_wipe_requests[chat_id] = {}
            cls.personal_wipe_requests[chat_id][user_id] = []
            cls.personal_wipe_requests[chat_id][user_id].append(datetime_now)
            necessary_requests = \
                config.personal_wipe_confirms - len(cls.personal_wipe_requests[chat_id][user_id])
            await event.respond(cls._msg_confirm_personal_wipe(full_name, necessary_requests))
            return False

    @classmethod
    async def _personal_wipe_messages(cls, event):
        """
        Clears all user's messages in chat
        """

        sender = await event.get_sender()
        user_id = sender.id
        try:
            async for message in event.client.iter_messages(
                    event.chat_id,
                    from_user=user_id
            ):
                try:
                    await message.delete()
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(
                        f"Error while deleting message: {str(e)}\n",
                        exc_info=True)
                    continue

            first_name = sender.first_name
            last_name = getattr(sender, 'last_name', None)
            full_name = f"{first_name} {last_name}" if last_name else first_name

            await event.reply(
                f"{cls.msg_complete}, {full_name}",
                file=os.path.join('images', 'pepe.png')
            )

        except Exception as e:
            logger.error(
                f"An error occurred while deleting user messages {user_id}: {e}\n",
                exc_info=True)
            await event.respond(f"An error occurred while deleting user messages {user_id}")

    @staticmethod
    def is_json_file(event):
        """filter for json file"""
        if not event.message.document:
            return False

        doc = event.message.document
        return (
                doc.mime_type == 'application/json' or
                (doc.file_name and doc.file_name.endswith('.json'))
        )

    @staticmethod
    def validate_json_structure(json_data, current_chat_id):
        try:
            if not json_data.get('name', None):
                return False
            if len(json_data.get('messages', list())) == 0:
                return False
            if json_data.get('id', None):
                if str(json_data['id']) in str(current_chat_id):
                    return True
            else:
                return False
        except Exception:
            return False



