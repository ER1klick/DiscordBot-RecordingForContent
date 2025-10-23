from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from ..models import User

async def get_or_create_user(session: AsyncSession, user_id: int, username: str) -> User:
    """Получает пользователя из БД или создает нового, если его нет."""
    result = await session.execute(select(User).filter_by(user_id=user_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(user_id=user_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    elif user.username != username:
        user.username = username
        await session.commit()
        
    return user

async def set_user_role(session: AsyncSession, user: User, role: str) -> User:
    """Устанавливает роль пользователю."""
    user.bot_role = role
    await session.commit()
    await session.refresh(user)
    return user