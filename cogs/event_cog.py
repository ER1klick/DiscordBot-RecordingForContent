import disnake
from disnake.ext import commands
import datetime
import re

from database.session import async_session_maker
from database.models import Event, BotRole, EventSlot
from database.crud import crud_event, crud_template, crud_user, crud_subscription
from .template_cog import autocomplete_template_name

# --- Вспомогательные функции и классы ---

def parse_datetime(datetime_str: str) -> int | None:
    """Парсит дату и время из строки в Unix timestamp."""
    datetime_str = datetime_str.strip()
    now = datetime.datetime.now()
    
    try:
        # Новый формат: "ЧЧ:ММ ДД.ММ"
        if re.match(r"^\d{2}:\d{2}\s\d{2}\.\d{2}$", datetime_str):
            dt_obj = datetime.datetime.strptime(datetime_str, "%H:%M %d.%m")
            dt_obj = dt_obj.replace(year=now.year)
            if dt_obj < now:
                dt_obj = dt_obj.replace(year=now.year + 1)
        # Новый формат: "ЧЧ:ММ ДД.ММ.ГГГГ"
        elif re.match(r"^\d{2}:\d{2}\s\d{2}\.\d{2}\.\d{4}$", datetime_str):
            dt_obj = datetime.datetime.strptime(datetime_str, "%H:%M %d.%m.%Y")
        # Старые форматы для обратной совместимости (время будет 00:00)
        elif re.match(r"^\d{2}\.\d{2}$", datetime_str):
            day, month = map(int, datetime_str.split('.'))
            dt_obj = datetime.datetime(now.year, month, day)
            if dt_obj < now:
                dt_obj = dt_obj.replace(year=now.year + 1)
        elif re.match(r"^\d{2}\.\d{2}\.\d{4}$", datetime_str):
            dt_obj = datetime.datetime.strptime(datetime_str, "%d.%m.%Y")
        else:
            return None
            
        return int(dt_obj.timestamp())
    except ValueError:
        return None

def format_event_embed(event: Event, guild: disnake.Guild) -> disnake.Embed:

    """Создает и форматирует Embed для анонса события."""
    embed = disnake.Embed(
        title=f"📅 {event.title}",
        description=event.description,
        color=disnake.Color.green()
    )
    embed.add_field(
        name="Время проведения",
        value=f"<t:{event.event_timestamp}:F> (<t:{event.event_timestamp}:R>)",
        inline=False
    )
    
    slot_texts = []
    for slot in sorted(event.slots, key=lambda s: s.slot_number):
        user_mention = f"<@{slot.signed_up_user_id}>" if slot.signed_up_user_id else "**[Свободно]**"
        slot_texts.append(f"`{slot.slot_number}.` {slot.role_name}: {user_mention}")
    
    embed.add_field(
        name="Участники",
        value="\n".join(slot_texts) or "Слоты не определены.",
        inline=False
    )
    
    owner = guild.get_member(event.owner_id)
    embed.set_footer(text=f"ID события: {event.id} | Организатор: {owner.display_name if owner else 'Неизвестно'}")
    return embed

class SignupModal(disnake.ui.Modal):
    def __init__(self, event: Event):
        self.event = event
        components = [
            disnake.ui.TextInput(
                label="Введите номер(а) слотов через запятую",
                placeholder="Например: 1 или 2, 4",
                custom_id="slot_input",
                style=disnake.TextInputStyle.short,
                max_length=50,
            ),
        ]
        super().__init__(title="Запись на событие", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        slot_input = inter.text_values["slot_input"]
        try:
            requested_slot_numbers = sorted(list(set(int(s.strip()) for s in slot_input.split(','))))
        except (ValueError, TypeError):
            await inter.followup.send("❌ Неверный формат. Введите только номера, разделенные запятой.", ephemeral=True)
            return

        valid_slots = [
            slot for slot in self.event.slots 
            if slot.slot_number in requested_slot_numbers and slot.signed_up_user_id is None
        ]
        if not valid_slots:
            await inter.followup.send("❌ Указанные слоты не существуют, заняты или введены неверно.", ephemeral=True)
            return
        
        await inter.response.defer(ephemeral=True)

        thread = inter.channel.get_thread(self.event.thread_id)
        if not thread:
            message = await inter.channel.fetch_message(self.event.message_id)
            thread = await message.create_thread(name=f"Заявки на '{self.event.title}'")
            async with async_session_maker() as session:
                await crud_event.update_event_thread_id(session, self.event.id, thread.id)
        
        async with async_session_maker() as session:
            for slot in valid_slots:
                msg = await thread.send(f"Пользователь {inter.author.mention} подал заявку на слот "
                                        f"`{slot.slot_number}. {slot.role_name}`. "
                                        f"Организатор <@{self.event.owner_id}>, подтвердите запись.")
                await msg.add_reaction("✅")
                await crud_event.create_signup_request(
                    session, message_id=msg.id, slot_id=slot.id, requester_id=inter.author.id
                )

        await inter.followup.send(f"✅ Ваши заявки на слоты: {', '.join(str(s.slot_number) for s in valid_slots)} "
                                  f"отправлены в ветку {thread.mention} на подтверждение.", ephemeral=True)


class SignupView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Записаться", style=disnake.ButtonStyle.success, custom_id="signup_button")
    async def signup_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        event_id_str = inter.message.embeds[0].footer.text.split(" | ")[0].replace("ID события: ", "")
        
        async with async_session_maker() as session:
            event = await crud_event.get_event_by_id(session, int(event_id_str))
            if not event:
                await inter.followup.send("Не удалось найти это событие. Возможно, оно было удалено.", ephemeral=True)
                return
        
        modal = SignupModal(event)
        await inter.response.send_modal(modal)

# --- Основной ког ---

class EventCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.view_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        """Этот метод вызывается, когда бот готов к работе."""
        if not self.view_added:
            self.bot.add_view(SignupView())
            self.view_added = True
            print("Persistent view 'SignupView' has been added.")

    @commands.slash_command(name="event", description="Команды для управления событиями")
    async def event(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @event.sub_command(name="create", description="Создать новое событие для записи")
    async def create(
        self,
        inter: disnake.ApplicationCommandInteraction,
        title: str = commands.Param(description="Название события"),
        description: str = commands.Param(description="Описание события"),
        date_time: str = commands.Param(description="Время и дата в формате 'ЧЧ:ММ ДД.ММ' или 'ЧЧ:ММ ДД.ММ.ГГГГ'"),
        template: str = commands.Param(default=None, description="Использовать готовый шаблон ролей", autocomplete=autocomplete_template_name),
        roles: str = commands.Param(default=None, description="Роли, разделенные '|', если не используется шаблон")
    ):
        await inter.response.defer(ephemeral=True)
        async with async_session_maker() as session:
            user = await crud_user.get_or_create_user(session, inter.author.id, inter.author.name)
            if user.bot_role not in [BotRole.EVENT_CREATOR, BotRole.ADMIN]:
                await inter.followup.send("У вас нет прав для создания событий.", ephemeral=True)
                return

            if not template and not roles:
                await inter.followup.send("Нужно указать либо шаблон, либо перечень ролей.", ephemeral=True)
                return
            if template and roles:
                await inter.followup.send("Нельзя одновременно использовать и шаблон, и ручной ввод ролей.", ephemeral=True)
                return
                
            role_list = []
            if template:
                db_template = await crud_template.get_template_by_name(session, inter.guild.id, template)
                if not db_template:
                    await inter.followup.send(f"Шаблон '{template}' не найден.", ephemeral=True)
                    return
                role_list = [r.role_name for r in db_template.roles]
            else:
                role_list = [r.strip() for r in roles.split('|') if r.strip()]

            if not role_list:
                await inter.followup.send("Не удалось определить список ролей.", ephemeral=True)
                return

            timestamp = parse_datetime(date_time)
            if not timestamp:
                await inter.followup.send("Неверный формат времени и даты. Используйте 'ЧЧ:ММ ДД.ММ' или 'ЧЧ:ММ ДД.ММ.ГГГГ'.", ephemeral=True)
                return
            
            new_event = await crud_event.create_event_with_slots(
                session, owner_id=inter.author.id, title=title, description=description,
                event_timestamp=timestamp, role_names=role_list
            )
            
            embed = format_event_embed(new_event, inter.guild)
            msg = await inter.channel.send(embed=embed, view=SignupView())
            await crud_event.update_event_message_info(session, new_event.id, msg.id, inter.channel.id)
            await inter.followup.send(f"Событие '{title}' успешно создано!", ephemeral=True)

            # Рассылка уведомлений подписчикам
            subscriber_ids = await crud_subscription.get_creator_subscribers(session, inter.author.id)
            if not subscriber_ids:
                return

            notification_text = f"Создатель событий {inter.author.mention} анонсировал новое событие в канале {inter.channel.mention}!"
            notification_embed = format_event_embed(new_event, inter.guild)
            success_count = 0
            for user_id in subscriber_ids:
                if user_id == inter.author.id:
                    continue
                try:
                    user_to_dm = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                    await user_to_dm.send(notification_text, embed=notification_embed)
                    success_count += 1
                except disnake.Forbidden:
                    print(f"Не удалось отправить ЛС пользователю {user_id}: личные сообщения заблокированы.")
                except Exception as e:
                    print(f"Произошла ошибка при отправке ЛС пользователю {user_id}: {e}")
            
            if success_count > 0:
                print(f"Уведомления о событии #{new_event.id} разосланы {success_count} подписчикам.")


    @commands.Cog.listener("on_raw_reaction_add")
    async def on_raw_reaction_add(self, payload: disnake.RawReactionActionEvent):
        
        if payload.user_id == self.bot.user.id or str(payload.emoji) != "✅":
            return

        async with async_session_maker() as session:
            request = await crud_event.get_signup_request(session, payload.message_id)
            if not request:
                return
            
            slot_result = await session.get(EventSlot, request.slot_id)
            if not slot_result: return
            event = await session.get(Event, slot_result.event_id)
            if not event: return

            # Проверяем, что реакцию поставил организатор события
            if payload.user_id != event.owner_id:
                return
            
            # Проверяем, свободен ли еще слот
            if slot_result.signed_up_user_id is not None:
                return

            await crud_event.assign_user_to_slot(session, request.slot_id, request.requester_id)
            updated_event = await crud_event.get_event_by_id(session, event.id)
            
            try:
                channel = self.bot.get_channel(updated_event.channel_id) or await self.bot.fetch_channel(updated_event.channel_id)
                message = await channel.fetch_message(updated_event.message_id)
                new_embed = format_event_embed(updated_event, payload.member.guild)
                await message.edit(embed=new_embed)
            except (disnake.NotFound, disnake.Forbidden) as e:
                print(f"Не удалось обновить сообщение для события {updated_event.id}: {e}")

            try:
                thread = self.bot.get_channel(updated_event.thread_id) or await self.bot.fetch_channel(updated_event.thread_id)
                request_message = await thread.fetch_message(request.request_message_id)
                await request_message.edit(content=f"✅ Заявка от <@{request.requester_id}> на слот "
                                                    f"`{slot_result.slot_number}. {slot_result.role_name}` **одобрена**.")
                await request_message.clear_reactions()
            except (disnake.NotFound, disnake.Forbidden) as e:
                print(f"Не удалось обновить сообщение в ветке для события {updated_event.id}: {e}")

def setup(bot: commands.Bot):
    bot.add_cog(EventCog(bot))