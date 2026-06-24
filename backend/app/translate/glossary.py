"""용어집 관리. 문서별 용어 일관성 유지."""
import re
from ..models.ir import GlossaryEntry, IRDocument


class GlossaryManager:
    def __init__(self, entries: list[GlossaryEntry] | None = None):
        self._entries: list[GlossaryEntry] = entries or []

    def add(self, src: str, tgt: str) -> None:
        if not any(e.src == src for e in self._entries):
            self._entries.append(GlossaryEntry(src=src, tgt=tgt))

    def format_for_prompt(self) -> str:
        if not self._entries:
            return "(용어집 없음)"
        lines = [f"- {e.src} → {e.tgt}" for e in self._entries]
        return "\n".join(lines)

    def apply(self, text: str) -> str:
        """번역 완료 텍스트에 용어집을 강제 적용 (후처리)."""
        for entry in self._entries:
            text = re.sub(re.escape(entry.src), entry.tgt, text, flags=re.IGNORECASE)
        return text

    @classmethod
    def from_ir(cls, ir: IRDocument) -> "GlossaryManager":
        return cls(ir.glossary)
