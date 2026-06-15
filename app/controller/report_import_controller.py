"""测评报告上传与解析 API。"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.deps import report_import_service
from app.dto.report_import import ReportImportResponse
from app.security.dependencies import get_current_user
from app.service.user_service import User

router = APIRouter(prefix="/api/report-import", tags=["测评报告导入"])


@router.post("/parse", response_model=ReportImportResponse, summary="上传 PDF/图片并解析测评报告")
async def parse_report(
    file: UploadFile = File(..., description="PDF 或图片（png/jpg/webp）"),
    advisory_type: str = Form(..., description="gaokao 或 career"),
    current_user: User = Depends(get_current_user),
) -> ReportImportResponse:
    """
    流程：PDF/图片 OCR → 语义重叠分块 → LLM 结构化抽取 → 预填画像。
    前端收到 report_context 后，分析时传入 imported_report_context，无需重复填写心理测评字段。
    """
    _ = current_user
    if advisory_type not in ("gaokao", "career"):
        raise HTTPException(status_code=400, detail="advisory_type 须为 gaokao 或 career")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件为空")

    try:
        return report_import_service.parse_upload(
            filename=file.filename or "upload",
            data=data,
            content_type=file.content_type,
            advisory_type=advisory_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"报告解析失败: {exc}") from exc
