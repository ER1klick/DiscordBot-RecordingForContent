import disnake
from disnake.ext import commands
from sqlalchemy.future import select

from database.session import async_session_maker
from database.models import User, BotRole
from database.crud.crud_user import get_or_create_user, set_user_role


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="admin",
        description="Административные команды"
    )
    @commands.is_owner() # Только владелец бота может использовать эти команды
    async def admin(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @admin.sub_command(name="setrole", description="Установить роль пользователю")
    async def set_role(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.User,
        role: str = commands.Param(choices=[BotRole.USER, BotRole.EVENT_CREATOR, BotRole.ADMIN])
    ):
        async with async_session_maker() as session:
            db_user = await get_or_create_user(session, user_id=user.id, username=user.name)
            await set_user_role(session, db_user, role)
        
        await inter.response.send_message(
            f"Пользователю {user.mention} была присвоена роль `{role}`.",
            ephemeral=True
        )

def setup(bot):
    bot.add_cog(AdminCog(bot))