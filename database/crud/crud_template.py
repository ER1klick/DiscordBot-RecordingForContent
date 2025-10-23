from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models import Template, TemplateRole

async def create_template_with_roles(
    session: AsyncSession, guild_id: int, name: str, role_names: list[str]
) -> Template:
    """Создает шаблон с набором ролей."""
    new_template = Template(guild_id=guild_id, name=name)
    new_template.roles = [TemplateRole(role_name=r) for r in role_names]
    
    session.add(new_template)
    await session.commit()
    await session.refresh(new_template)
    return new_template

async def get_template_by_name(session: AsyncSession, guild_id: int, name: str) -> Template | None:
    """Находит шаблон по имени на конкретном сервере."""
    result = await session.execute(
        select(Template).where(Template.guild_id == guild_id, Template.name == name)
    )
    return result.scalar_one_or_none()

async def get_all_templates_for_guild(session: AsyncSession, guild_id: int) -> Sequence[Template]:
    """Возвращает все шаблоны для указанного сервера."""
    result = await session.execute(
        select(Template).where(Template.guild_id == guild_id).order_by(Template.name)
    )
    return result.scalars().all()

async def delete_template(session: AsyncSession, guild_id: int, name: str) -> bool:
    """Удаляет шаблон по имени."""
    template = await get_template_by_name(session, guild_id, name)
    if template:
        await session.delete(template)
        await session.commit()
        return True
    return False