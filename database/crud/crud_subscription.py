from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from ..models import Subscription, User, BotRole

async def add_subscription(session: AsyncSession, subscriber_id: int, creator_id: int) -> Subscription:
    """Добавляет новую подписку в БД."""
    new_sub = Subscription(subscriber_id=subscriber_id, creator_id=creator_id)
    session.add(new_sub)
    await session.commit()
    return new_sub

async def remove_subscription(session: AsyncSession, subscriber_id: int, creator_id: int) -> bool:
    """Удаляет подписку из БД."""
    query = delete(Subscription).where(
        Subscription.subscriber_id == subscriber_id,
        Subscription.creator_id == creator_id
    )
    result = await session.execute(query)
    await session.commit()
    return result.rowcount > 0

async def get_user_subscriptions(session: AsyncSession, subscriber_id: int) -> Sequence[User]:
    """Получает список создателей, на которых подписан пользователь."""
    query = select(User).join(Subscription, User.user_id == Subscription.creator_id).where(
        Subscription.subscriber_id == subscriber_id
    )
    result = await session.execute(query)
    return result.scalars().all()

async def get_creator_subscribers(session: AsyncSession, creator_id: int) -> Sequence[int]:
    """Получает список ID пользователей, подписанных на создателя."""
    query = select(Subscription.subscriber_id).where(Subscription.creator_id == creator_id)
    result = await session.execute(query)
    return result.scalars().all()

async def get_all_creators(session: AsyncSession) -> Sequence[User]:
    """Получает список всех пользователей с ролью 'event_creator'."""
    query = select(User).where(User.bot_role == BotRole.EVENT_CREATOR)
    result = await session.execute(query)
    return result.scalars().all()