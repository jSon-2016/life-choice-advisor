"""PDF / 图片测评报告文字提取。"""

from __future__ import annotations

import base64
import logging
import os
from io import BytesIO

logger = logging.getLogger(__name__)

ALLOWED_MIME = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/bmp",
}


def extract_text_from_upload(filename: str, data: bytes, content_type: str | None) -> tuple[str, list[str]]:
    """返回 (全文, warnings)。"""
    mime = _resolve_mime(filename, content_type)
    if mime not in ALLOWED_MIME:
        raise ValueError(f"不支持的文件类型: {mime or filename}")

    warnings: list[str] = []
    if mime == "application/pdf":
        text, pdf_warn = _extract_pdf(data)
        warnings.extend(pdf_warn)
    else:
        text, img_warn = _extract_image_ocr(data, mime)
        warnings.extend(img_warn)

    if len(text.strip()) < 30:
        raise ValueError("未能从文件中提取有效文字，请尝试更清晰的图片或可选中文字的 PDF")
    return text, warnings


def _resolve_mime(filename: str, content_type: str | None) -> str:
    if content_type and content_type.split(";")[0].strip() in ALLOWED_MIME:
        return content_type.split(";")[0].strip().lower()
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "application/pdf"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith(".webp"):
        return "image/webp"
    return (content_type or "application/octet-stream").split(";")[0].strip().lower()


def _extract_pdf(data: bytes) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("缺少 pypdf 依赖，请 pip install pypdf") from exc

    reader = PdfReader(BytesIO(data))
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(f"## PDF 第{i + 1}页\n{page_text.strip()}")

    text = "\n\n".join(pages)
    if len(text.strip()) < 80:
        warnings.append(
            "PDF 可能是扫描件，文本提取较少；建议导出为图片后重新上传，或上传更清晰的截图。"
        )
    return text, warnings


def _extract_image_ocr(data: bytes, mime: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if not os.getenv("DASHSCOPE_API_KEY"):
        raise RuntimeError("图片 OCR 需要配置 DASHSCOPE_API_KEY")

    try:
        from dashscope import MultiModalConversation
    except ImportError as exc:
        raise RuntimeError("缺少 dashscope 依赖") from exc

    b64 = base64.b64encode(data).decode("ascii")
    messages = [
        {
            "role": "user",
            "content": [
                {"image": f"data:{mime};base64,{b64}"},
                {
                    "text": (
                        "请完整提取图片中的测评报告文字。"
                        "保留表格结构（可用 Markdown 表格），"
                        "包含各维度名称、得分、参考标准/常模、解读说明。"
                        "不要总结，不要遗漏数字。"
                    )
                },
            ],
        }
    ]
    response = MultiModalConversation.call(model="qwen-vl-plus", messages=messages)
    if getattr(response, "status_code", None) not in (None, 200):
        raise RuntimeError(f"图片 OCR 失败: {getattr(response, 'message', response)}")

    text = _parse_multimodal_text(response)
    if not text.strip():
        warnings.append("OCR 返回为空，请检查图片清晰度")
    return text, warnings


def _parse_multimodal_text(response) -> str:
    try:
        content = response.output.choices[0].message.content
        if isinstance(content, list):
            parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("text")]
            return "\n".join(parts)
        if isinstance(content, str):
            return content
    except Exception as exc:
        logger.warning("解析 OCR 响应失败: %s", exc)
    return str(response)
