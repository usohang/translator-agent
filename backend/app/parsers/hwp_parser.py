"""HWP / HWPX → IR 변환.
우선순위: hwp-hwpx-parser → pyhwp → LibreOffice DOCX 변환 fallback.
"""
from pathlib import Path
import subprocess
import tempfile
import shutil

from ..models.ir import IRDocument, Block, BlockType, StyleHint, TableData
from .base import BaseParser
from .docx_parser import DocxParser


def _try_hwp_hwpx_parser(file_path: Path, images_dir: Path) -> IRDocument | None:
    try:
        from hwp_hwpx_parser import HwpFile  # type: ignore
    except ImportError:
        return None

    try:
        images_dir.mkdir(parents=True, exist_ok=True)
        hwp = HwpFile(str(file_path))
        doc_ir = IRDocument(
            source_format=file_path.suffix.lstrip(".").lower(),
            source_path=str(file_path),
            images_dir=str(images_dir),
        )
        order = 0
        page_num = 1

        for para in hwp.paragraphs():
            text = para.text.strip()
            if not text:
                continue
            is_heading = getattr(para, "is_heading", False)
            level = getattr(para, "heading_level", None)
            doc_ir.blocks.append(Block(
                type=BlockType.HEADING if is_heading else BlockType.PARAGRAPH,
                level=level,
                original_page=page_num,
                order=order,
                text_src=text,
            ))
            order += 1

        for i, img_bytes in enumerate(hwp.images()):
            img_name = f"hwp_img_{i}.png"
            img_path = images_dir / img_name
            img_path.write_bytes(img_bytes)
            doc_ir.blocks.append(Block(
                type=BlockType.IMAGE,
                original_page=1,
                order=order,
                image_ref=str(img_path),
            ))
            order += 1

        return doc_ir
    except Exception:
        return None


def _try_libreoffice_fallback(file_path: Path, images_dir: Path) -> IRDocument | None:
    """LibreOffice headless 로 HWP→DOCX 변환 후 DocxParser 재사용."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None

    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            [soffice, "--headless", "--convert-to", "docx", "--outdir", tmp, str(file_path)],
            capture_output=True, timeout=120,
        )
        if result.returncode != 0:
            return None

        converted = list(Path(tmp).glob("*.docx"))
        if not converted:
            return None

        doc_ir = DocxParser().parse(converted[0], images_dir)
        doc_ir.source_format = file_path.suffix.lstrip(".").lower()
        doc_ir.source_path = str(file_path)
        return doc_ir


class HwpParser(BaseParser):

    def parse(self, file_path: Path, images_dir: Path) -> IRDocument:
        # 1순위: hwp-hwpx-parser
        result = _try_hwp_hwpx_parser(file_path, images_dir)
        if result:
            return result

        # 2순위: LibreOffice fallback
        result = _try_libreoffice_fallback(file_path, images_dir)
        if result:
            return result

        raise RuntimeError(
            f"HWP 파싱 실패: hwp-hwpx-parser와 LibreOffice 모두 사용할 수 없습니다. "
            f"pip install hwp-hwpx-parser 또는 LibreOffice를 설치하세요."
        )
