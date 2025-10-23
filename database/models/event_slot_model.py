from sqlalchemy import BigInteger, ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base

class EventSlot(Base):
    __tablename__ = "event_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    slot_number: Mapped[int] = mapped_column(Integer)
    role_name: Mapped[str] = mapped_column(String(100))
    signed_up_user_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    
    event: Mapped["Event"] = relationship(back_populates="slots")