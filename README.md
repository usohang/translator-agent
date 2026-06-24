# 문서 번역 에이전트 (Document Translation Agent)

PDF·HWP·DOCX 등 문서 파일을 업로드하면 **Claude AI 기반 문맥 번역**으로 한글 DOCX를 생성하는 번역 에이전트입니다.

## 주요 기능

- **문맥 기반 2-pass 번역**: 초벌 번역 → Claude 검수 패스로 품질 보장
- **레이아웃 보존**: 제목 계층·표·이미지·스타일 재현
- **원문 추적**: 번역본에 `〔원문 p.N〕` 표기 + 페이지 매핑 표 첨부
- **용어집**: 동일 문서 내 핵심 용어 일관성 유지
- **웹 대시보드**: 드래그&드롭 업로드 → 실시간 진행률(SSE) → 다운로드

## 아키텍처

```
[Next.js 대시보드]
       │ 업로드/SSE/다운로드
       ▼
[FastAPI 백엔드]
       │ 작업 생성
       ▼
[Celery Worker + Redis]
       ▼
PDF/HWP/DOCX → IR → Claude 번역 → DOCX 출력
```

## 빠른 시작 (Docker Compose)

```bash
# 1. 환경 변수 설정
cp .env.example .env
# .env 파일에서 ANTHROPIC_API_KEY 입력

# 2. 전체 스택 실행
docker compose up --build

# 3. 브라우저에서 열기
open http://localhost:3000
```

## 로컬 개발

### 백엔드

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Redis 실행 (별도 터미널)
docker run -p 6379:6379 redis:7-alpine

# FastAPI 서버
uvicorn app.main:app --reload --port 8000

# Celery 워커 (별도 터미널)
celery -A app.jobs.celery_app worker --loglevel=info
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

## 프로젝트 구조

```
├── backend/
│   └── app/
│       ├── models/ir.py          # IR 데이터 모델 (Pydantic)
│       ├── parsers/              # PDF · HWP · DOCX → IR
│       ├── translate/            # Claude API 번역 + 용어집
│       ├── assemble/             # IR → DOCX 생성
│       ├── pagemap/              # 원문↔번역본 페이지 매핑
│       ├── jobs/                 # Celery 파이프라인
│       └── api/routes.py         # FastAPI 엔드포인트
├── frontend/src/
│   ├── app/page.tsx              # 메인 대시보드
│   ├── components/               # UploadZone · ProgressCard · JobList
│   └── lib/api.ts                # API 클라이언트 (SSE 포함)
├── docker-compose.yml
├── .env.example                  # 환경 변수 템플릿
└── 원문번역 에이전트_기획서.md    # 전체 설계 문서
```

## 지원 포맷

| 입력 | 파서 |
|------|------|
| `.pdf` | PyMuPDF (fitz) |
| `.hwp` / `.hwpx` | hwp-hwpx-parser → LibreOffice fallback |
| `.docx` | python-docx |

**출력**: `.docx` (기본) — 편집·재활용 최적화

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 프론트엔드 | Next.js 14, React, Tailwind CSS, SSE |
| 백엔드 API | Python FastAPI |
| 작업 큐 | Celery + Redis |
| 번역 엔진 | Anthropic Claude API |
| DOCX 출력 | python-docx |

## 설계 문서

전체 시스템 설계·파이프라인·데이터 모델: [원문번역 에이전트_기획서.md](원문번역%20에이전트_기획서.md)
