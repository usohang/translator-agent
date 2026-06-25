"""번역 모듈 — Google Gemini API 2-pass 번역 (초벌 → 검수)."""
from __future__ import annotations
import re
import uuid
from typing import Callable

from google import genai

from ..models.ir import Block, BlockType, IRDocument
from ..config import get_settings
from .glossary import GlossaryManager

PROTECTED_RE = re.compile(
    r'(?:'
    r'https?://\S+'
    r'|\b\d[\d,.%]*\s*(?:[a-zA-Z]{1,5})?\b'
    r'|`[^`]+`'
    r'|\$[^$]+\$'
    r')',
    re.UNICODE,
)

TRANSLATE_PROMPT = """\
당신은 전문 번역가입니다. 원문의 의미·뉘앙스·논조를 보존하되 자연스러운 한국어로 옮깁니다.

규칙:
1. {{TOKEN_...}} 형태의 토큰은 번역하지 말고 그대로 유지합니다.
2. 표·목록 구조(| 구분자 등)는 그대로 유지합니다.
3. 아래 용어집을 반드시 따릅니다.
4. 번역문만 출력합니다. 설명·주석 금지.

[도메인] {domain}
[용어집]
{glossary}
[직전 맥락] {ctx_prev}
[다음 맥락] {ctx_next}
[번역할 블록]
{text}"""

REVIEW_PROMPT = """\
번역 검수 전문가로서 아래 초벌 번역을 검토하세요:
1. 원문 의미 누락·오역을 수정합니다.
2. 어색한 한국어 표현을 자연스럽게 다듬습니다.
3. 보호 토큰({{TOKEN_...}})이 그대로인지 확인합니다.
수정된 최종 번역문만 출력합니다.

[원문]
{original}

[초벌 번역]
{draft}"""


def _protect_tokens(text: str) -> tuple[str, dict[str, str]]:
    token_map: dict[str, str] = {}

    def replacer(m: re.Match) -> str:
        key = f"{{{{TOKEN_{uuid.uuid4().hex[:6].upper()}}}}}"
        token_map[key] = m.group(0)
        return key

    return PROTECTED_RE.sub(replacer, text), token_map


def _restore_tokens(text: str, token_map: dict[str, str]) -> str:
    for key, val in token_map.items():
        text = text.replace(key, val)
    return text


def _detect_domain(ir: IRDocument) -> str:
    sample = " ".join(b.text_src for b in ir.blocks[:20] if b.text_src)
    if re.search(r"contract|agreement|법률|계약|조항", sample, re.I):
        return "법률"
    if re.search(r"clinical|patient|diagnosis|의학|환자|진단", sample, re.I):
        return "의학"
    if re.search(r"abstract|methodology|hypothesis|논문|연구|실험", sample, re.I):
        return "학술"
    return "일반"


class Translator:
    def __init__(self) -> None:
        cfg = get_settings()
        self._client = genai.Client(api_key=cfg.google_api_key)
        self._primary_model = cfg.gemini_model_primary
        self._light_model = cfg.gemini_model_light

    def translate_document(
        self,
        ir: IRDocument,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> IRDocument:
        glossary = GlossaryManager.from_ir(ir)
        domain = _detect_domain(ir)

        translatable = [
            b for b in ir.blocks
            if b.type not in (BlockType.IMAGE, BlockType.PAGE_BREAK) and b.text_src.strip()
        ]
        total = len(translatable)

        for idx, block in enumerate(translatable):
            ctx_prev = self._context_text(ir.blocks, block.order, -1)
            ctx_next = self._context_text(ir.blocks, block.order, +1)
            protected, token_map = _protect_tokens(block.text_src)

            # 1-pass: 초벌 번역
            draft = self._call(
                self._primary_model,
                TRANSLATE_PROMPT.format(
                    domain=domain,
                    glossary=glossary.format_for_prompt(),
                    ctx_prev=ctx_prev,
                    ctx_next=ctx_next,
                    text=protected,
                ),
            )

            # 2-pass: heading 또는 긴 블록만 검수
            if block.type == BlockType.HEADING or len(block.text_src) > 300:
                draft = self._call(
                    self._light_model,
                    REVIEW_PROMPT.format(original=protected, draft=draft),
                )

            block.text_tgt = glossary.apply(_restore_tokens(draft, token_map))
            block.protected_tokens = token_map

            if progress_cb:
                progress_cb(idx + 1, total)

        return ir

    def _context_text(self, blocks: list[Block], order: int, direction: int) -> str:
        target = order + direction
        for b in blocks:
            if b.order == target and b.text_src:
                return b.text_src[:200]
        return ""

    def _call(self, model: str, prompt: str) -> str:
        import time
        for attempt in range(5):
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                return response.text.strip()
            except Exception as e:
                msg = str(e)
                if "503" in msg or "UNAVAILABLE" in msg or "429" in msg:
                    wait = 20 * (attempt + 1)
                    print(f"  Gemini 일시 오류, {wait}초 후 재시도 ({attempt+1}/5)...")
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError("Gemini API 재시도 초과")
