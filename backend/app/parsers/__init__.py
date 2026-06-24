from pathlib import Path
from ..models.ir import IRDocument


def get_parser(file_path: Path):
    """확장자에 맞는 파서 반환."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        from .pdf_parser import PDFParser
        return PDFParser()
    if suffix in (".hwp", ".hwpx"):
        from .hwp_parser import HwpParser
        return HwpParser()
    if suffix == ".docx":
        from .docx_parser import DocxParser
        return DocxParser()
    raise ValueError(f"지원하지 않는 포맷: {suffix}")


def parse_document(file_path: Path, images_dir: Path) -> IRDocument:
    parser = get_parser(file_path)
    return parser.parse(file_path, images_dir)
