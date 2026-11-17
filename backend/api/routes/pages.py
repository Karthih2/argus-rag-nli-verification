"""Page image from the original PDF, with an optional evidence highlight box."""

import io

import pypdfium2 as pdfium
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from PIL import ImageDraw

from backend.api.deps import get_or_404
from backend.db.client import chunks, documents, get_fs

router = APIRouter(tags=["pages"])

SCALE = 2
HIGHLIGHT_FILL = (0, 230, 118, 40)  # --green from the design tokens, translucent
HIGHLIGHT_LINE = (0, 230, 118, 200)


@router.get("/documents/{document_id}/pages/{page_num}.png")
def page_image(document_id: str, page_num: int, highlight: str | None = None):
    """Render one page as PNG; ?highlight=<chunk_id> draws that chunk's box."""
    doc = get_or_404(documents(), document_id, "Document")
    pdf = pdfium.PdfDocument(get_fs().get(ObjectId(doc["file"]["gridfs_id"])).read())
    if not 1 <= page_num <= len(pdf):
        raise HTTPException(404, f"Page {page_num} not found (document has {len(pdf)} pages)")
    image = pdf[page_num - 1].render(scale=SCALE).to_pil()

    chunk = chunks().find_one({"_id": highlight, "document_id": document_id}) if highlight else None
    if chunk and chunk.get("bbox") and chunk.get("page") == page_num:
        w, h = image.size
        x0, y0, x1, y1 = chunk["bbox"]
        ImageDraw.Draw(image, "RGBA").rectangle(
            [x0 * w, y0 * h, x1 * w, y1 * h], fill=HIGHLIGHT_FILL, outline=HIGHLIGHT_LINE, width=3
        )
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return Response(buf.getvalue(), media_type="image/png")
