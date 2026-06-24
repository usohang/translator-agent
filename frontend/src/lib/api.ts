export interface JobProgress {
  job_id: string;
  status: "QUEUED" | "PARSING" | "TRANSLATING" | "ASSEMBLING" | "DONE" | "ERROR";
  progress: number;
  current_step: string;
  translated_blocks: number;
  total_blocks: number;
  error_message?: string;
  output_path?: string;
}

const BASE = "/api";

export async function uploadFile(file: File): Promise<{ job_id: string; filename: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/jobs`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `업로드 실패 (${res.status})`);
  }
  return res.json();
}

export async function getJob(jobId: string): Promise<JobProgress> {
  const res = await fetch(`${BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error(`작업 조회 실패 (${res.status})`);
  return res.json();
}

export function streamJob(
  jobId: string,
  onMessage: (p: JobProgress) => void,
  onDone: () => void,
  onError: (e: string) => void,
): () => void {
  const es = new EventSource(`${BASE}/jobs/${jobId}/stream`);
  es.onmessage = (e) => {
    const data = JSON.parse(e.data) as JobProgress;
    onMessage(data);
    if (data.status === "DONE" || data.status === "ERROR") {
      es.close();
      if (data.status === "DONE") onDone();
      else onError(data.error_message ?? "오류가 발생했습니다.");
    }
  };
  es.onerror = () => {
    es.close();
    onError("SSE 연결이 끊어졌습니다.");
  };
  return () => es.close();
}

export function downloadUrl(jobId: string): string {
  return `${BASE}/jobs/${jobId}/download`;
}

export async function deleteJob(jobId: string): Promise<void> {
  await fetch(`${BASE}/jobs/${jobId}`, { method: "DELETE" });
}
