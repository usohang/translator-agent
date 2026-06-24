"""번역 파이프라인 Celery 태스크.
QUEUED → PARSING → TRANSLATING → ASSEMBLING → DONE / ERROR
"""
from __future__ import annotations
import json
from pathlib import Path

from .celery_app import celery_app
from ..models.ir import JobStatus, JobProgress
from ..config import get_settings


def _save_progress(job_id: str, progress: JobProgress) -> None:
    """진행 상태를 Redis(Celery backend)에 저장."""
    celery_app.backend.set(  # type: ignore[attr-defined]
        f"job_progress:{job_id}",
        progress.model_dump_json().encode(),
        ex=86400,
    )


def load_progress(job_id: str) -> JobProgress | None:
    raw = celery_app.backend.get(f"job_progress:{job_id}")  # type: ignore[attr-defined]
    if not raw:
        return None
    return JobProgress.model_validate_json(raw)


@celery_app.task(bind=True, name="pipeline.translate_document")
def translate_document_task(self, job_id: str, file_path: str, options: dict) -> dict:
    cfg = get_settings()
    progress = JobProgress(job_id=job_id, status=JobStatus.QUEUED, progress=0)
    _save_progress(job_id, progress)

    try:
        # ── Step 1: Parse ──────────────────────────────────────────
        progress.status = JobStatus.PARSING
        progress.current_step = "문서 구조 추출 중..."
        progress.progress = 5
        _save_progress(job_id, progress)

        src = Path(file_path)
        images_dir = Path(cfg.images_dir) / job_id

        from ..parsers import parse_document
        ir = parse_document(src, images_dir)

        progress.total_blocks = len([b for b in ir.blocks if b.text_src.strip()])
        progress.progress = 20
        _save_progress(job_id, progress)

        # ── Step 2: Translate ──────────────────────────────────────
        progress.status = JobStatus.TRANSLATING
        progress.current_step = "번역 중..."
        _save_progress(job_id, progress)

        from ..translate import Translator

        def on_block_done(done: int, total: int) -> None:
            progress.translated_blocks = done
            progress.total_blocks = total
            progress.progress = 20 + int(done / max(total, 1) * 65)
            progress.current_step = f"번역 중... ({done}/{total})"
            _save_progress(job_id, progress)

        translator = Translator()
        ir = translator.translate_document(ir, progress_cb=on_block_done)

        progress.progress = 85
        _save_progress(job_id, progress)

        # ── Step 3: Assemble ──────────────────────────────────────
        progress.status = JobStatus.ASSEMBLING
        progress.current_step = "DOCX 생성 중..."
        progress.progress = 88
        _save_progress(job_id, progress)

        output_dir = Path(cfg.output_dir) / job_id
        output_path = output_dir / f"{src.stem}_translated.docx"

        from ..assemble.docx_builder import build_docx
        build_docx(ir, output_path)

        # ── Done ──────────────────────────────────────────────────
        progress.status = JobStatus.DONE
        progress.progress = 100
        progress.current_step = "완료"
        progress.output_path = str(output_path)
        _save_progress(job_id, progress)

        return {"status": "DONE", "output_path": str(output_path)}

    except Exception as exc:
        progress.status = JobStatus.ERROR
        progress.error_message = str(exc)
        progress.progress = 0
        _save_progress(job_id, progress)
        raise
