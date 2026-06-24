"""DOCX → IR 변환. python-docx 기반."""
from pathlib import Path
import re

from ..models.ir import (
    IRDocument, Block, BlockType, StyleHint, TableData,
)
from .base import BaseParser

try:
    from docx import Document as DocxDocument
    from docx.oxml.ns import qn
    import lxml.etree as etree
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


class DocxParser(BaseParser):

    def parse(self, file_path: Path, images_dir: Path) -> IRDocument:
        if not DOCX_AVAILABLE:
            raise RuntimeError("python-docx가 설치되지 않았습니다.")

        images_dir.mkdir(parents=True, exist_ok=True)
        doc_ir = IRDocument(
            source_format="docx",
            source_path=str(file_path),
            images_dir=str(images_dir),
        )

        docx = DocxDocument(str(file_path))
        order = 0
        page_num = 1

        # 이미지 추출 (relationships 기반)
        img_map: dict[str, str] = {}
        for rel in docx.part.rels.values():
            if "image" in rel.reltype:
                try:
                    img_name = Path(rel.target_ref).name
                    img_path = images_dir / img_name
                    img_path.write_bytes(rel.target_part.blob)
                    img_map[rel.rId] = str(img_path)
                except Exception:
                    pass

        body_elements = list(docx.element.body)
        for elem in body_elements:
            tag = etree.QName(elem).localname

            # 단락
            if tag == "p":
                text = "".join(r.text or "" for r in elem.iter(qn("w:t")))
                text = text.strip()
                if not text:
                    # 페이지 브레이크 감지
                    if elem.find(".//" + qn("w:lastRenderedPageBreak")) is not None:
                        page_num += 1
                    continue

                style_name = ""
                pPr = elem.find(qn("w:pPr"))
                if pPr is not None:
                    pStyle = pPr.find(qn("w:pStyle"))
                    if pStyle is not None:
                        style_name = pStyle.get(qn("w:val"), "")

                level = _heading_level_from_style(style_name)
                font_size, bold = _extract_run_style(elem)
                if level is None:
                    level = self._infer_heading_level(font_size, bold)

                btype = BlockType.HEADING if level else BlockType.PARAGRAPH
                doc_ir.blocks.append(Block(
                    type=btype,
                    level=level,
                    original_page=page_num,
                    order=order,
                    text_src=text,
                    style_hint=StyleHint(font_size=font_size, bold=bold),
                ))
                order += 1

            # 표
            elif tag == "tbl":
                table_data = _parse_table_elem(elem)
                all_text = " | ".join(
                    cell for row in [table_data.headers] + table_data.rows for cell in row
                )
                doc_ir.blocks.append(Block(
                    type=BlockType.TABLE,
                    original_page=page_num,
                    order=order,
                    text_src=all_text,
                    table=table_data,
                ))
                order += 1

        doc_ir.total_pages = page_num
        return doc_ir


def _heading_level_from_style(style_name: str) -> int | None:
    s = style_name.lower()
    if re.match(r"heading\s*1|제목\s*1|h1", s):
        return 1
    if re.match(r"heading\s*2|제목\s*2|h2", s):
        return 2
    if re.match(r"heading\s*3|제목\s*3|h3", s):
        return 3
    return None


def _extract_run_style(elem) -> tuple[float, bool]:
    sizes = []
    bolds = []
    from docx.oxml.ns import qn
    for rPr in elem.iter(qn("w:rPr")):
        sz = rPr.find(qn("w:sz"))
        if sz is not None:
            try:
                sizes.append(int(sz.get(qn("w:val"), "22")) / 2)
            except ValueError:
                pass
        b = rPr.find(qn("w:b"))
        bolds.append(b is not None)
    font_size = max(sizes) if sizes else 11.0
    bold = any(bolds)
    return font_size, bold


def _parse_table_elem(elem) -> TableData:
    from docx.oxml.ns import qn
    rows_data: list[list[str]] = []
    for tr in elem.iter(qn("w:tr")):
        cells = []
        for tc in tr.iter(qn("w:tc")):
            cell_text = "".join(t.text or "" for t in tc.iter(qn("w:t"))).strip()
            cells.append(cell_text)
        rows_data.append(cells)
    if not rows_data:
        return TableData()
    return TableData(headers=rows_data[0], rows=rows_data[1:])
