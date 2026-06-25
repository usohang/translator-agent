"""엔드투엔드 테스트: PDF 업로드 → 번역 → DOCX 다운로드."""
import time
import requests
from pathlib import Path

BASE = "http://localhost:8000/api"
PDF = Path("test_sample.pdf")

print("=== 1. PDF 업로드 ===")
with open(PDF, "rb") as f:
    resp = requests.post(f"{BASE}/jobs", files={"file": (PDF.name, f, "application/pdf")})
resp.raise_for_status()
data = resp.json()
job_id = data["job_id"]
print(f"job_id: {job_id}")

print("\n=== 2. 번역 진행 대기 ===")
for i in range(120):
    time.sleep(2)
    p = requests.get(f"{BASE}/jobs/{job_id}").json()
    status = p["status"]
    pct = p["progress"]
    step = p.get("current_step", "")
    print(f"  [{pct:3d}%] {status} - {step}")
    if status == "DONE":
        print(f"\n번역 완료! 출력: {p['output_path']}")
        break
    if status == "ERROR":
        print(f"\n오류 발생: {p['error_message']}")
        break
else:
    print("타임아웃")
    exit(1)

print("\n=== 3. DOCX 다운로드 ===")
dl = requests.get(f"{BASE}/jobs/{job_id}/download")
dl.raise_for_status()
out = Path("test_output.docx")
out.write_bytes(dl.content)
print(f"저장 완료: {out} ({len(dl.content):,} bytes)")
