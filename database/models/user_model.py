from sqlalchemy import BigInteger, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base

class BotRole:
    USER = "user"
    EVENT_CREATOR = "event_creator"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str] = mapped_column(String(255))
    balance: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    bot_role: Mapped[str] = mapped_column(String(50), default=BotRole.USER, server_default=BotRole.USER, nullable=False)
    
    # Связь: один пользователь может создать много событий
    events: Mapped[list["Event"]] = relationship(back_populates="owner")