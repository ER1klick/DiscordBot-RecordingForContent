import disnake
from disnake.ext import commands
from sqlalchemy.exc import IntegrityError

from database.session import async_session_maker
from database.crud import crud_template

# Функция для автодополнения
async def autocomplete_template_name(inter: disnake.ApplicationCommandInteraction, user_input: str):
    async with async_session_maker() as session:
        templates = await crud_template.get_all_templates_for_guild(session, inter.guild.id)
        return [t.name for t in templates if user_input.lower() in t.name.lower()]

class TemplateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="template", description="Управление шаблонами ролей")
    async def template(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @template.sub_command(name="create", description="Создать новый шаблон")
    async def create(
        self,
        inter: disnake.ApplicationCommandInteraction,
        name: str = commands.Param(description="Название шаблона (например, 'Рейд 10ппл')"),
        roles: str = commands.Param(description="Роли, разделенные символом '|' (например, 'танк|хил|дд')")
    ):
        role_list = [r.strip() for r in roles.split('|') if r.strip()]
        if not role_list:
            await inter.followup.send("Вы не указали ни одной роли!", ephemeral=True)
            return

        async with async_session_maker() as session:
            try:
                await crud_template.create_template_with_roles(
                    session, guild_id=inter.guild.id, name=name, role_names=role_list
                )
                await inter.followup.send(
                    f"✅ Шаблон **{name}** успешно создан!", ephemeral=True
                )
            except IntegrityError:
                await inter.followup.send(
                    f"❌ Шаблон с именем **{name}** уже существует на этом сервере.", ephemeral=True
                )

    @template.sub_command(name="list", description="Показать все шаблоны на сервере")
    async def list(self, inter: disnake.ApplicationCommandInteraction):
        async with async_session_maker() as session:
            templates = await crud_template.get_all_templates_for_guild(session, inter.guild.id)
        
        if not templates:
            await inter.followup.send("На этом сервере еще нет ни одного шаблона.", ephemeral=True)
            return

        embed = disnake.Embed(
            title="📋 Шаблоны ролей на этом сервере",
            color=disnake.Color.blurple()
        )
        for t in templates:
            # Получаем роли через атрибут .roles
            role_names = ", ".join([r.role_name for r in t.roles]) if t.roles else "Нет ролей"
            embed.add_field(name=f"🔹 {t.name}", value=f"`{role_names}`", inline=False)
        
        await inter.followup.send(embed=embed, ephemeral=True)

    @template.sub_command(name="delete", description="Удалить шаблон")
    async def delete(
        self,
        inter: disnake.ApplicationCommandInteraction,
        name: str = commands.Param(description="Название шаблона для удаления", autocomplete=autocomplete_template_name)
    ):
        
        async with async_session_maker() as session:
            success = await crud_template.delete_template(session, inter.guild.id, name)
        
        if success:
            await inter.followup.send(f"🗑️ Шаблон **{name}** был удален.", ephemeral=True)
        else:
            await inter.followup.send(f"❓ Не удалось найти шаблон **{name}**.", ephemeral=True)


def setup(bot):
    bot.add_cog(TemplateCog(bot))