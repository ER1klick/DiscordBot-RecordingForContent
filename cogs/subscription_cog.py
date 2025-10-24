import disnake
from disnake.ext import commands
from sqlalchemy.exc import IntegrityError

from database.session import async_session_maker
from database.models import User, BotRole
from database.crud import crud_subscription, crud_user

# --- Функция автодополнения для поиска ивент-креаторов ---
async def autocomplete_event_creators(inter: disnake.ApplicationCommandInteraction, user_input: str):
    async with async_session_maker() as session:
        creators = await crud_subscription.get_all_creators(session)
        return [
            creator.username for creator in creators 
            if user_input.lower() in creator.username.lower()
        ]

class SubscriptionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="subscription", description="Управление подписками на создателей событий")
    async def subscription(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @subscription.sub_command(name="subscribe", description="Подписаться на уведомления от создателя событий")
    async def subscribe(
        self,
        inter: disnake.ApplicationCommandInteraction,
        creator: disnake.User = commands.Param(description="Пользователь, на которого вы хотите подписаться")
    ):
        async with async_session_maker() as session:
            # Проверяем, является ли целевой пользователь ивент-креатором
            target_user = await crud_user.get_or_create_user(session, creator.id, creator.name)
            if target_user.bot_role != BotRole.EVENT_CREATOR:
                await inter.response.send_message(
                    f"❌ Нельзя подписаться на {creator.mention}, так как он не является создателем событий.",
                    ephemeral=True
                )
                return
            
            try:
                await crud_subscription.add_subscription(session, inter.author.id, creator.id)
                await inter.response.send_message(
                    f"✅ Вы успешно подписались на уведомления от {creator.mention}!",
                    ephemeral=True
                )
            except IntegrityError: # Эта ошибка возникнет, если подписка уже существует
                await inter.response.send_message(
                    f"Вы уже подписаны на {creator.mention}.",
                    ephemeral=True
                )
    
    @subscription.sub_command(name="unsubscribe", description="Отписаться от уведомлений создателя событий")
    async def unsubscribe(
        self,
        inter: disnake.ApplicationCommandInteraction,
        creator: disnake.User = commands.Param(description="Пользователь, от которого вы хотите отписаться")
    ):
        async with async_session_maker() as session:
            success = await crud_subscription.remove_subscription(session, inter.author.id, creator.id)
            if success:
                await inter.response.send_message(
                    f"🗑️ Вы отписались от уведомлений {creator.mention}.",
                    ephemeral=True
                )
            else:
                await inter.response.send_message(
                    f"Вы не были подписаны на {creator.mention}.",
                    ephemeral=True
                )

    @subscription.sub_command(name="list", description="Показать список ваших подписок")
    async def list_subscriptions(self, inter: disnake.ApplicationCommandInteraction):
        async with async_session_maker() as session:
            subscriptions = await crud_subscription.get_user_subscriptions(session, inter.author.id)

        if not subscriptions:
            await inter.response.send_message("У вас пока нет активных подписок.", ephemeral=True)
            return

        embed = disnake.Embed(
            title="🔔 Ваши подписки",
            description="Вы получаете уведомления о новых событиях от следующих пользователей:",
            color=disnake.Color.blurple()
        )
        sub_list = [f"- <@{user.user_id}>" for user in subscriptions]
        embed.add_field(name="Создатели событий", value="\n".join(sub_list))
        await inter.response.send_message(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(SubscriptionCog(bot))