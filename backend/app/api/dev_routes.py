"""개발 모드 라우터 — Celery/Redis 없이 BackgroundTasks + 인메모리 상태로 동작."""
from __future__ import annotations
import asyncio
import json
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse

from ..config import get_settings
from ..models.ir import JobProgress, JobStatus

router = APIRouter(prefix="/api")
cfg = get_settings()

_jobs: dict[str, JobProgress] = {}

ALLOWED_EXTENSIONS = {".pdf", ".hwp", ".hwpx", ".docx"}
MAX_BYTES = cfg.max_file_size_mb * 1024 * 1024


@router.post("/jobs")
async def create_job(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"지원하지 않는 형식: {suffix}")

    job_id = str(uuid.uuid4())
    upload_dir = Path(cfg.upload_dir) / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest = upload_dir / (file.filename or f"document{suffix}")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"파일 크기 초과 (최대 {cfg.max_file_size_mb}MB)")
    dest.write_bytes(data)

    _jobs[job_id] = JobProgress(job_id=job_id, status=JobStatus.QUEUED, progress=0)
    background_tasks.add_task(_run_pipeline, job_id, str(dest))

    return {"job_id": job_id, "status": "QUEUED", "filename": file.filename}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    return _jobs[job_id]


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    async def generator():
        while True:
            p = _jobs.get(job_id)
            if not p:
                yield f"data: {json.dumps({'error': 'not_found'})}\n\n"
                break
            yield f"data: {p.model_dump_json()}\n\n"
            if p.status in (JobStatus.DONE, JobStatus.ERROR):
                break
            await asyncio.sleep(1)

    return StreamingResponse(generator(), media_type="text/event-stream")


@router.get("/jobs/{job_id}/download")
async def download_result(job_id: str):
    p = _jobs.get(job_id)
    if not p:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    if p.status != JobStatus.DONE:
        raise HTTPException(400, f"아직 완료되지 않았습니다. 현재 상태: {p.status}")
    if not p.output_path or not Path(p.output_path).exists():
        raise HTTPException(500, "출력 파일이 없습니다.")
    return FileResponse(
        p.output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=Path(p.output_path).name,
    )


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    _jobs.pop(job_id, None)
    for base in (cfg.upload_dir, cfg.output_dir):
        d = Path(base) / job_id
        if d.exists():
            shutil.rmtree(d)
    return {"deleted": job_id}


# ── 파이프라인 (백그라운드 실행) ────────────────────────────────────────
def _update(job_id: str, **kwargs):
    p = _jobs[job_id]
    for k, v in kwargs.items():
        setattr(p, k, v)


async def _run_pipeline(job_id: str, file_path: str):
    import asyncio
    from pathlib import Path as P

    try:
        _update(job_id, status=JobStatus.PARSING, current_step="문서 구조 추출 중...", progress=5)
        await asyncio.sleep(0)  # 이벤트 루프에 제어권 반납

        src = P(file_path)
        images_dir = P(cfg.images_dir) / job_id

        # 동기 파서를 스레드풀에서 실행
        import concurrent.futures, functools
        loop = asyncio.get_event_loop()

        from ..parsers import parse_document
        with concurrent.futures.ThreadPoolExecutor() as pool:
            ir = await loop.run_in_executor(pool, functools.partial(parse_document, src, images_dir))

        total = len([b for b in ir.blocks if b.text_src.strip()])
        _update(job_id, total_blocks=total, progress=20)

        _update(job_id, status=JobStatus.TRANSLATING, current_step="번역 중...")

        from ..translate import Translator
        translator = Translator()

        done_count = 0

        def on_block(done: int, total_: int):
            nonlocal done_count
            done_count = done
            pct = 20 + int(done / max(total_, 1) * 65)
            _update(
                job_id,
                translated_blocks=done,
                total_blocks=total_,
                progress=pct,
                current_step=f"번역 중... ({done}/{total_})",
            )

        with concurrent.futures.ThreadPoolExecutor() as pool:
            ir = await loop.run_in_executor(
                pool, functools.partial(translator.translate_document, ir, on_block)
            )

        _update(job_id, status=JobStatus.ASSEMBLING, current_step="DOCX 생성 중...", progress=88)

        output_dir = P(cfg.output_dir) / job_id
        output_path = output_dir / f"{src.stem}_translated.docx"

        from ..assemble.docx_builder import build_docx
        with concurrent.futures.ThreadPoolExecutor() as pool:
            await loop.run_in_executor(pool, functools.partial(build_docx, ir, output_path))

        _update(
            job_id,
            status=JobStatus.DONE,
            progress=100,
            current_step="완료",
            output_path=str(output_path),
        )

    except Exception as exc:
        _update(job_id, status=JobStatus.ERROR, error_message=str(exc), progress=0)
        raise
