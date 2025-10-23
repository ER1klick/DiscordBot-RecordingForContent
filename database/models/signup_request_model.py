from sqlalchemy import BigInteger, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from ..base import Base

class SignupRequest(Base):
    __tablename__ = "signup_requests"

    request_message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    slot_id: Mapped[int] = mapped_column(ForeignKey("event_slots.id"))
    requester_id: Mapped[int] = mapped_column(BigInteger)