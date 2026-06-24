"""번역 모듈 — Claude API 2-pass 번역 (초벌 → 검수)."""
from __future__ import annotations
import re
import uuid
from typing import Callable

import anthropic

from ..models.ir import Block, BlockType, IRDocument
from ..config import get_settings
from .glossary import GlossaryManager

PROTECTED_RE = re.compile(
    r'(?:'
    r'https?://\S+'          # URL
    r'|\b\d[\d,.%]*\s*(?:[a-zA-Z]{1,5})?\b'  # 숫자+단위
    r'|`[^`]+`'              # 코드 인라인
    r'|\$[^$]+\$'            # 수식
    r')',
    re.UNICODE,
)

TRANSLATE_SYSTEM = """\
당신은 전문 번역가입니다. 원문의 의미·뉘앙스·논조를 보존하되 자연스러운 한국어로 옮깁니다.

규칙:
1. {{TOKEN_...}} 형태의 토큰은 번역하지 말고 그대로 유지합니다.
2. 표·목록 구조(| 구분자 등)는 그대로 유지합니다.
3. 아래 용어집을 반드시 따릅니다.
4. 번역문만 출력합니다. 설명·주석 금지.
"""

REVIEW_SYSTEM = """\
당신은 번역 검수 전문가입니다. 아래 초벌 번역을 검토하여:
1. 원문 의미 누락·오역을 수정합니다.
2. 어색한 한국어 표현을 자연스럽게 다듬습니다.
3. 보호 토큰({{TOKEN_...}})이 그대로 남아 있는지 확인합니다.
수정된 최종 번역문만 출력합니다.
"""


def _protect_tokens(text: str) -> tuple[str, dict[str, str]]:
    """번역하면 안 되는 요소를 플레이스홀더로 치환."""
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
        self._client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
        self._primary = cfg.claude_model_primary
        self._light = cfg.claude_model_light
        self._batch = cfg.translation_batch_size
        self._ctx_n = cfg.max_context_blocks

    def translate_document(
        self,
        ir: IRDocument,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> IRDocument:
        glossary = GlossaryManager.from_ir(ir)
        domain = _detect_domain(ir)

        # 번역 대상 블록만 추출 (이미지·페이지 브레이크 제외)
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
            draft = self._call_translate(
                domain=domain,
                glossary=glossary.format_for_prompt(),
                ctx_prev=ctx_prev,
                ctx_next=ctx_next,
                text=protected,
                model=self._primary,
            )

            # 2-pass: 검수 (heading 이상만, paragraph는 생략해서 비용 절감)
            if block.type == BlockType.HEADING or len(block.text_src) > 300:
                draft = self._call_review(
                    original=protected,
                    draft=draft,
                    model=self._light,
                )

            block.text_tgt = glossary.apply(_restore_tokens(draft, token_map))
            block.protected_tokens = token_map

            if progress_cb:
                progress_cb(idx + 1, total)

        return ir

    def _context_text(self, blocks: list[Block], order: int, direction: int) -> str:
        target = order + direction
        result = []
        for b in blocks:
            if b.order == target and b.text_src:
                result.append(b.text_src[:200])
        return result[0] if result else ""

    def _call_translate(
        self, domain: str, glossary: str, ctx_prev: str, ctx_next: str, text: str, model: str
    ) -> str:
        user_msg = (
            f"[도메인] {domain}\n"
            f"[용어집]\n{glossary}\n"
            f"[직전 맥락] {ctx_prev}\n"
            f"[다음 맥락] {ctx_next}\n"
            f"[번역할 블록]\n{text}"
        )
        msg = self._client.messages.create(
            model=model,
            max_tokens=2048,
            system=TRANSLATE_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return msg.content[0].text.strip()  # type: ignore[index]

    def _call_review(self, original: str, draft: str, model: str) -> str:
        user_msg = f"[원문]\n{original}\n\n[초벌 번역]\n{draft}"
        msg = self._client.messages.create(
            model=model,
            max_tokens=2048,
            system=REVIEW_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        return msg.content[0].text.strip()  # type: ignore[index]
