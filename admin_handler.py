from telethon import events
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
from telethon.errors import ChatAdminRequiredError
import asyncio
from config import config
import datetime
import os


"""
telethon documentation
https://docs.telethon.dev/en/stable/basic/updates.html
"""


class GroupWipeHandlerMessages:
    """
    Этот класс содержит текст и функции формирования текстовых сообщений.
    Является родительским классом для <GroupWipeHandler>
    Не содержит никакой логики использования модуля <telethon>, только работа с текстом
    """

    cmd_total_wipe = '/wipe_total'
    cmd_personal_wipe = '/wipe_myself'
    cmd_help = '/help'
    msg_run_global_wipe = "Запускаю глобальный вайп сообщений в данном групповом чате..."
    msg_run_personal_wipe = "Запускаю вайп истории сообщений пользователя"
    msg_permission_denied = "❗️ Необходимы права администатора для выполнения данной процедуры"
    msg_help = "Для удаления ВСЕХ сообщений отправьте в чат:\n" + \
               f"<code>{cmd_total_wipe}</code>\n" \
               f"<i>- запросить глобальную очистку " + \
               "(требуется 3 запрос(а) от разных пользователей в течении суток)</i>\n\n" + \
               "Для удаления своих сообщений отправьте в чат:\n" + \
               f"<code>{cmd_personal_wipe}</code>\n" \
               f"<i>- очистка сообщений пользователя (далее необходимо повторно отправить " \
               f"команду для подтверждения, во избежания ложного срабатывания)</i>\n\n" + \
               "🔄 Через 24 часа все запросы сбрасываются.\n\n" + \
               "Для получения справки отправьте в чат:\n"  + \
               f"<code>{cmd_help}</code>"

    msg_about_bot = '<b>Приветствую!</b>\n' \
                    'Этот бот создан для того,что бы экстренно удалить всю историю сообщений ' \
                    'внутри этого группового чата по запросу участников.\n' + \
                    'Так же имеется опция удалить все свои сообщения (определённого пользователя) в группе.\n\n' + \
                    '❕ Для корректной работы необходимо выдать боту права администратора.\n\n' \
                    '❕ Так же если группа содержит более 100 сообщений, необходимо открыть всю историю сообщений.\n' \
                    'Для этого необходимо зайти в пункт меню ⚙️ <i>"Управление группой"</i>.\n' + \
                    'Далее найти опцию ⚙️ <i>"История чата для новых участников"</i> и сменить флаг на <i>"Видна"</i>\n\n'
    msg_complete = "✅ Готово"

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
    Данный класс подключается в главном модуле при инициализации экземпляра класса TelegramBot.
    Класс содержит логику взаимодействия с сообщениями в групповых чатах Telegram (удаление сообщений).
    Наследуется от класса <GroupWipeHandlerMessages>, который содержит текст.
    Логика взаимодействия с сообщениями осуществляется через отправление пользователями в групповой чат определённых
    команд (GroupWipeHandlerMessages.cmd_total_wipe, GroupWipeHandlerMessages.cmd_personal_wipe и т.д.).
    Главный метод async def message_handler отлавливает все сообщения пользователей в групповом чате (через фильтр), и
    в случае наличия в сообщении одной из команд запускает соответствующий обработчик.
    """

    # В этом атрибуте хранятся объекты запросов на глобальное удаление сообщений в чатах
    total_wipe_requests = {}  # {chat_id: {user_id: date_time, user_id: date_time, ..}, chat_id: {...}, ...}

    # В этом атрибуте хранятся объекты запросов на персональное удаление сообщений (конкретных пользователе) в чатах
    personal_wipe_requests = {}  # {chat_id: {user_id: [date_time, date_time], user_id: [...], ...}, chat_id: {...} ...}

    @classmethod
    def register(cls, client):

        # # Хендлер для добавления в группу
        @client.on(events.ChatAction())
        async def chat_action_handler(event):
            if event.user_added and event.is_channel:
                await event.respond(cls.msg_about_bot + cls.msg_help, parse_mode='html')

        @client.on(events.NewMessage(func=lambda e: e.is_group))
        async def _message_handler(event):
            event_text_split: list = event.text.split()
            if not event.text:  # Если входящая мессага пустая
                return
            if cls.cmd_total_wipe in event_text_split:
                # Проверяет наличие админских прав у бота в текущем групповом чате
                if not await cls._is_bot_admin(event):
                    # Уведомление о том, что необходимы права администратора
                    await event.respond(cls.msg_permission_denied)
                    return
                # Проверяет наличие достаточного количества запросов от пользователей для инициализации удаления
                confirm: bool = await cls._confirm_total_wipe(event)
                if confirm:
                    # Удаляет все сообщения ВСЕХ пользователей внутри группового чата
                    await cls._total_wipe_messages(event)
                    return
                else:
                    return

            elif cls.cmd_personal_wipe in event_text_split:
                # Проверяет наличие админских прав у бота в текущем групповом чате
                if not await cls._is_bot_admin(event):
                    # Уведомление о том, что необходимы права администратора
                    await event.respond(cls.msg_permission_denied)
                    return
                # Проверяет наличие достаточного количества запросов от пользователей для инициализации удаления
                confirm: bool = await cls._confirm_personal_wipe(event)
                if confirm:
                    # Удаляет все сообщения ОПРЕДЕЛЁННОГО пользователя внутри группового чата
                    await cls._personal_wipe_messages(event)
                    return
                else:
                    return

            elif cls.cmd_help in event_text_split:
                await event.respond(cls.msg_help, parse_mode='html')
                return

            else:
                return


    @classmethod
    async def _is_bot_admin(cls, event) -> bool:
        """
        Проверяет, является ли бот администратором группы с правами удаления сообщений
        """
        try:
            # Getting information about yourself <https://docs.telethon.dev/en/stable/basic/quick-start.html>
            me = await event.client.get_me()

            # Getting information about chat
            chat = await event.get_chat()

            # Для супергрупп/каналов
            if hasattr(chat, 'admin_rights'):
                # Проверяем права бота
                if chat.admin_rights and chat.admin_rights.delete_messages:
                    return True
            # Получаем полную информацию о правах
            try:
                permissions = await event.client.get_permissions(chat.id, me.id)

                # Проверяем права администратора
                if isinstance(permissions.participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
                    # Проверяем конкретное право на удаление сообщений
                    if isinstance(permissions.participant, ChannelParticipantCreator):
                        return True  # Создатель имеет все права

                    if isinstance(permissions.participant, ChannelParticipantAdmin):
                        return permissions.participant.admin_rights.delete_messages
            except ChatAdminRequiredError:
                pass

            return False

        except Exception as e:
            print(f"Ошибка при проверке прав администратора: {e}")
            return False

    @classmethod
    async def _confirm_total_wipe(cls, event) -> bool:

        datetime_now = datetime.datetime.now()
        sender = await event.get_sender()
        chat_id = event.chat_id
        user_id = sender.id

        if cls.total_wipe_requests.get(chat_id, None):
            # Если ключ с chat_id уже существует в  cls.total_wipe_requests -> обойти содержимое
            for key, value in cls.total_wipe_requests[chat_id].items():
                # key - user_id, value - datetime
                time_difference = abs(datetime_now - value)
                # Если дельта времени хотя бу у одного элементы более суток - очищаем словарь
                if not time_difference < datetime.timedelta(days=1):
                    cls.total_wipe_requests[chat_id].clear()
                    break

            cls.total_wipe_requests[chat_id][user_id] = datetime_now
            if len(cls.total_wipe_requests[chat_id].keys()) >= config.total_wipe_confirms:
                # Если достигнуто необходимое количество запросов участников на вайп для данного чата
                # очищаем словарь и возвращаем разрешение True (разрешение на запуск вайпа)
                cls.total_wipe_requests[chat_id].clear()
                await event.respond(cls.msg_run_global_wipe)
                return True
            else:
                await event.respond(cls._msg_confirm_total_wipe(
                    len((cls.total_wipe_requests[chat_id].keys())),
                    config.total_wipe_confirms - len(cls.total_wipe_requests[chat_id].keys()))
                )
                return False
        else:
            cls.total_wipe_requests[chat_id] = {}
            cls.total_wipe_requests[chat_id][user_id] = datetime_now

            await event.respond(cls._msg_confirm_total_wipe(
                len((cls.total_wipe_requests[chat_id].keys())),
                config.total_wipe_confirms - len(cls.total_wipe_requests[chat_id].keys()))
            )
            return False

    @classmethod
    async def _total_wipe_messages(cls, event):
        """Метод для полной очистки чата"""

        try:
            count = 0
            async for message in event.client.iter_messages(event.chat_id):
                try:
                    await message.delete()
                    count += 1
                    if count % 10 == 0:  # Отчет каждые 10 сообщений
                        print(f"Удалено {count} сообщений")
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"Ошибка при удалении сообщения: {e}")
                    continue

            await event.reply(
                cls.msg_complete,
                file=os.path.join('files', 'pepe.png')
            )
        except Exception as e:
            print(f"Критическая ошибка: {e}")
            await event.respond("❌ Произошла ошибка при очистке чата")

    @classmethod
    async def _confirm_personal_wipe(cls, event) -> bool:

        datetime_now = datetime.datetime.now()
        sender = await event.get_sender()
        chat_id = event.chat_id
        user_id = sender.id
        first_name = sender.first_name  # Имя (обязательное поле)
        last_name = getattr(sender, 'last_name', None)  # Фамилия (может отсутствовать)
        # Полное имя (комбинация имени и фамилии)
        full_name = f"{first_name} {last_name}" if last_name else first_name

        if cls.personal_wipe_requests.get(chat_id, None):
            # Если ключ с chat_id уже существует в  cls.personal_wipe_requests -> обойти содержимое: list[datetime, ...]
            if cls.personal_wipe_requests[chat_id].get(user_id, None):
                if len(cls.personal_wipe_requests[chat_id][user_id]) > 0:
                    for datetime_item in cls.personal_wipe_requests[chat_id][user_id]:
                        # Проверяем дату_время каждого запроса (должен быть не старше суток)
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
        Удаляет все сообщения указанного пользователя в текущем чате
        """
        sender = await event.get_sender()
        user_id = sender.id
        try:
            # Получаем сообщения только от конкретного пользователя
            async for message in event.client.iter_messages(
                    event.chat_id,
                    from_user=user_id
            ):
                try:
                    await message.delete()
                    await asyncio.sleep(0.5)  # Увеличиваем задержку для безопасности
                except Exception as e:
                    print(f"Ошибка при удалении сообщения {message.id}: {e}")
                    continue

            # Получаем информацию о пользователе для красивого отчета
            first_name = sender.first_name  # Имя (обязательное поле)
            last_name = getattr(sender, 'last_name', None)  # Фамилия (может отсутствовать)
            # Полное имя (комбинация имени и фамилии)
            full_name = f"{first_name} {last_name}" if last_name else first_name

            await event.reply(
                f"{cls.msg_complete}, {full_name}",
                file=os.path.join('files', 'pepe.png')
            )

        except Exception as e:
            print(f"An error occurred while deleting user messages {user_id}: {e}")
            await event.respond(f"An error occurred while deleting user messages {user_id}")
