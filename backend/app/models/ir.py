"""Intermediate Representation (IR) — 모든 포맷을 공통 구조로 정규화한 문서 모델."""
from __future__ import annotations
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
import uuid


class BlockType(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    IMAGE = "image"
    CAPTION = "caption"
    LIST = "list"
    PAGE_BREAK = "page_break"


class StyleHint(BaseModel):
    font_size: float | None = None
    bold: bool = False
    italic: bool = False
    align: str = "left"
    color: str | None = None


class TableData(BaseModel):
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class Block(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: BlockType
    level: int | None = None          # heading 계층 (1~3)
    original_page: int = 0
    order: int = 0
    text_src: str = ""
    text_tgt: str = ""
    style_hint: StyleHint = Field(default_factory=StyleHint)
    table: TableData | None = None
    image_ref: str | None = None      # 추출된 이미지 파일 경로
    protected_tokens: dict[str, str] = Field(default_factory=dict)


class GlossaryEntry(BaseModel):
    src: str
    tgt: str


class PageMapEntry(BaseModel):
    tgt_page: str = ""
    src_page: str
    section: str = ""


class IRDocument(BaseModel):
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_format: str = ""
    source_path: str = ""
    language_src: str = "en"
    language_tgt: str = "ko"
    total_pages: int = 0
    glossary: list[GlossaryEntry] = Field(default_factory=list)
    blocks: list[Block] = Field(default_factory=list)
    page_map: list[PageMapEntry] = Field(default_factory=list)
    images_dir: str = ""


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    PARSING = "PARSING"
    TRANSLATING = "TRANSLATING"
    ASSEMBLING = "ASSEMBLING"
    DONE = "DONE"
    ERROR = "ERROR"


class JobProgress(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = 0           # 0~100
    current_step: str = ""
    translated_blocks: int = 0
    total_blocks: int = 0
    error_message: str | None = None
    output_path: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
