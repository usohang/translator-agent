"""PDF → IR 변환. PyMuPDF(fitz) 기반."""
from pathlib import Path
import re

from ..models.ir import (
    IRDocument, Block, BlockType, StyleHint, TableData,
)
from .base import BaseParser

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False


class PDFParser(BaseParser):

    def parse(self, file_path: Path, images_dir: Path) -> IRDocument:
        if not FITZ_AVAILABLE:
            raise RuntimeError("PyMuPDF가 설치되지 않았습니다. pip install pymupdf")

        images_dir.mkdir(parents=True, exist_ok=True)
        doc_ir = IRDocument(
            source_format="pdf",
            source_path=str(file_path),
            images_dir=str(images_dir),
        )

        pdf = fitz.open(str(file_path))
        doc_ir.total_pages = len(pdf)
        order = 0

        for page_num, page in enumerate(pdf, start=1):
            blocks_raw = page.get_text("dict")["blocks"]  # type: ignore[union-attr]

            for raw in blocks_raw:
                btype = raw.get("type", -1)

                # 이미지 블록
                if btype == 1:
                    img_name = f"p{page_num}_{order}.png"
                    img_path = images_dir / img_name
                    try:
                        pix = fitz.Pixmap(pdf, raw["xref"])  # type: ignore[arg-type]
                        if pix.n > 4:
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        pix.save(str(img_path))
                        doc_ir.blocks.append(Block(
                            type=BlockType.IMAGE,
                            original_page=page_num,
                            order=order,
                            image_ref=str(img_path),
                        ))
                        order += 1
                    except Exception:
                        pass
                    continue

                # 텍스트 블록
                if btype != 0:
                    continue

                for line_data in raw.get("lines", []):
                    spans = line_data.get("spans", [])
                    if not spans:
                        continue
                    text = " ".join(s["text"] for s in spans).strip()
                    if not text:
                        continue

                    # 대표 span의 스타일 정보
                    rep = max(spans, key=lambda s: len(s["text"]))
                    font_size = rep.get("size", 11.0)
                    bold = bool(rep.get("flags", 0) & 0b10000)

                    style = StyleHint(font_size=font_size, bold=bold)
                    level = self._infer_heading_level(font_size, bold)

                    btype_ir = BlockType.HEADING if level else BlockType.PARAGRAPH
                    doc_ir.blocks.append(Block(
                        type=btype_ir,
                        level=level,
                        original_page=page_num,
                        order=order,
                        text_src=text,
                        style_hint=style,
                    ))
                    order += 1

        pdf.close()
        return doc_ir


def _is_table_line(text: str) -> bool:
    return bool(re.search(r"\t|\|", text))
