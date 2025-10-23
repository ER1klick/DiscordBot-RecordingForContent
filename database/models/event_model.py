from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    thread_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    event_timestamp: Mapped[int] = mapped_column(BigInteger)

    owner: Mapped["User"] = relationship(back_populates="events")
    slots: Mapped[list["EventSlot"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", lazy="selectin"
    )