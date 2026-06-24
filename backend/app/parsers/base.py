from abc import ABC, abstractmethod
from pathlib import Path
from ..models.ir import IRDocument


class BaseParser(ABC):
    """모든 파서의 공통 인터페이스."""

    @abstractmethod
    def parse(self, file_path: Path, images_dir: Path) -> IRDocument:
        """파일을 읽어 IRDocument로 변환한다."""

    def _infer_heading_level(self, font_size: float, is_bold: bool) -> int | None:
        if font_size >= 18 or (font_size >= 16 and is_bold):
            return 1
        if font_size >= 14 or (font_size >= 13 and is_bold):
            return 2
        if font_size >= 12 and is_bold:
            return 3
        return None
