from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base

class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(100))

    roles: Mapped[list["TemplateRole"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", lazy="selectin"
    )
    
    __table_args__ = (UniqueConstraint("guild_id", "name", name="uq_guild_template_name"),)