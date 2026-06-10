"""报告 DTO。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ReportSummary(BaseModel):
    report_id: str = Field(..., alias="reportId")
    report_type: str = Field(..., alias="reportType")
    title: str | None = None
    summary: str | None = None
    created_at: datetime = Field(..., alias="createdAt")

    model_config = {"populate_by_name": True}


class ReportDetail(ReportSummary):
    input_json: dict = Field(..., alias="inputJson")
    result_json: dict = Field(..., alias="resultJson")

    model_config = {"populate_by_name": True}
