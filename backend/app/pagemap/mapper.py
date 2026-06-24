"""원문 ↔ 번역본 페이지 매핑 테이블 생성."""
from ..models.ir import IRDocument, PageMapEntry


def build_page_map(ir: IRDocument) -> list[PageMapEntry]:
    """블록의 original_page를 기준으로 섹션별 매핑표를 생성한다."""
    entries: list[PageMapEntry] = []
    current_src_page = 0
    current_section = ""
    tgt_page_start = 1
    tgt_page_counter = 1

    for block in ir.blocks:
        # 새 섹션 감지 (H1 heading)
        if block.type and hasattr(block.type, "value") and block.type.value == "heading" and block.level == 1:
            if current_src_page > 0:
                entries.append(PageMapEntry(
                    tgt_page=f"{tgt_page_start}",
                    src_page=str(current_src_page),
                    section=current_section,
                ))
            current_section = block.text_tgt or block.text_src
            tgt_page_start = tgt_page_counter

        if block.original_page != current_src_page:
            current_src_page = block.original_page
            tgt_page_counter += 1

    if current_src_page > 0:
        entries.append(PageMapEntry(
            tgt_page=f"{tgt_page_start}–{tgt_page_counter}",
            src_page=str(current_src_page),
            section=current_section,
        ))

    ir.page_map = entries
    return entries
