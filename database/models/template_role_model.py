from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base

class TemplateRole(Base):
    __tablename__ = "template_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"))
    role_name: Mapped[str] = mapped_column(String(100))

    template: Mapped["Template"] = relationship(back_populates="roles")