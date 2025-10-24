# database/models/subscription_model.py
from sqlalchemy import BigInteger, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..base import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    subscriber_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))

    __table_args__ = (
        PrimaryKeyConstraint("subscriber_id", "creator_id"),
    )