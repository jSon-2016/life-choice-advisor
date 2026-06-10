"""ORM 模型。"""

from datetime import datetime

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AdvisoryReportModel(Base):
    __tablename__ = "t_advisory_report"
    __table_args__ = (Index("idx_report_user_created", "user_id", "created_at"),)

    report_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    report_type: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str | None] = mapped_column(String(128))
    summary: Mapped[str | None] = mapped_column(String(512))
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
