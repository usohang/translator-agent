"""FastAPI 라우터 — 업로드 / 진행률(SSE) / 다운로드."""
from __future__ import annotations
import asyncio
import json
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse

from ..config import get_settings
from ..models.ir import JobProgress, JobStatus
from ..jobs.pipeline import translate_document_task, load_progress

router = APIRouter(prefix="/api")
cfg = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".hwp", ".hwpx", ".docx"}
MAX_BYTES = cfg.max_file_size_mb * 1024 * 1024


@router.post("/jobs")
async def create_job(file: UploadFile = File(...)):
    """파일 업로드 → 번역 작업 생성."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"지원하지 않는 형식: {suffix}. 허용: {ALLOWED_EXTENSIONS}")

    job_id = str(uuid.uuid4())
    upload_dir = Path(cfg.upload_dir) / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest = upload_dir / (file.filename or f"document{suffix}")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"파일 크기 초과 (최대 {cfg.max_file_size_mb}MB)")

    dest.write_bytes(data)

    translate_document_task.apply_async(
        args=[job_id, str(dest), {}],
        task_id=job_id,
    )

    return {"job_id": job_id, "status": "QUEUED", "filename": file.filename}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """작업 진행 상태 단발 조회."""
    progress = load_progress(job_id)
    if not progress:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    return progress


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    """SSE — 실시간 진행률 스트리밍."""
    async def event_generator():
        while True:
            progress = load_progress(job_id)
            if not progress:
                yield _sse({"error": "not_found"})
                break
            yield _sse(progress.model_dump())
            if progress.status in (JobStatus.DONE, JobStatus.ERROR):
                break
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/jobs/{job_id}/download")
async def download_result(job_id: str):
    """번역 완료 DOCX 다운로드."""
    progress = load_progress(job_id)
    if not progress:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    if progress.status != JobStatus.DONE:
        raise HTTPException(400, f"아직 완료되지 않았습니다. 현재 상태: {progress.status}")
    if not progress.output_path or not Path(progress.output_path).exists():
        raise HTTPException(500, "출력 파일을 찾을 수 없습니다.")

    return FileResponse(
        progress.output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=Path(progress.output_path).name,
    )


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """작업 및 관련 파일 삭제."""
    for base in (cfg.upload_dir, cfg.output_dir):
        job_dir = Path(base) / job_id
        if job_dir.exists():
            shutil.rmtree(job_dir)
    return {"deleted": job_id}


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
