from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from ..models import Event, EventSlot, SignupRequest

async def create_event_with_slots(
    session: AsyncSession, owner_id: int, title: str, description: str, 
    event_timestamp: int, role_names: list[str]
) -> Event:
    """Создает событие и все его слоты."""
    new_event = Event(
        owner_id=owner_id,
        title=title,
        description=description,
        event_timestamp=event_timestamp
    )
    new_event.slots = [
        EventSlot(slot_number=i + 1, role_name=role) 
        for i, role in enumerate(role_names)
    ]
    session.add(new_event)
    await session.commit()
    await session.refresh(new_event)
    return new_event

async def get_event_by_id(session: AsyncSession, event_id: int) -> Event | None:
    """Получает событие по его ID, подгружая слоты."""
    result = await session.execute(
        select(Event).options(selectinload(Event.slots)).filter_by(id=event_id)
    )
    return result.scalar_one_or_none()

async def update_event_message_info(
    session: AsyncSession, event_id: int, message_id: int, channel_id: int
) -> None:
    """Обновляет ID сообщения и канала для события."""
    event = await get_event_by_id(session, event_id)
    if event:
        event.message_id = message_id
        event.channel_id = channel_id
        await session.commit()

async def update_event_thread_id(session: AsyncSession, event_id: int, thread_id: int) -> None:
    """Обновляет ID ветки для события."""
    event = await get_event_by_id(session, event_id)
    if event:
        event.thread_id = thread_id
        await session.commit()

async def create_signup_request(
    session: AsyncSession, message_id: int, slot_id: int, requester_id: int
) -> SignupRequest:
    """Создает запрос на запись в ветке."""
    request = SignupRequest(
        request_message_id=message_id, 
        slot_id=slot_id, 
        requester_id=requester_id
    )
    session.add(request)
    await session.commit()
    return request

async def get_signup_request(session: AsyncSession, message_id: int) -> SignupRequest | None:
    """Получает запрос на запись по ID его сообщения."""
    result = await session.execute(
        select(SignupRequest).filter_by(request_message_id=message_id)
    )
    return result.scalar_one_or_none()

async def assign_user_to_slot(session: AsyncSession, slot_id: int, user_id: int) -> EventSlot | None:
    """Записывает пользователя на слот."""
    result = await session.execute(
        select(EventSlot).filter_by(id=slot_id)
    )
    slot = result.scalar_one_or_none()
    if slot:
        slot.signed_up_user_id = user_id
        await session.commit()
        await session.refresh(slot)
    return slot