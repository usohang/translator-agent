"use client";
import { JobProgress } from "@/lib/api";
import clsx from "clsx";

const STATUS_LABEL: Record<JobProgress["status"], string> = {
  QUEUED: "대기 중",
  PARSING: "문서 구조 분석",
  TRANSLATING: "번역 중",
  ASSEMBLING: "DOCX 생성",
  DONE: "완료",
  ERROR: "오류",
};

const STATUS_COLOR: Record<JobProgress["status"], string> = {
  QUEUED: "bg-gray-200 text-gray-600",
  PARSING: "bg-yellow-100 text-yellow-700",
  TRANSLATING: "bg-blue-100 text-blue-700",
  ASSEMBLING: "bg-purple-100 text-purple-700",
  DONE: "bg-green-100 text-green-700",
  ERROR: "bg-red-100 text-red-700",
};

interface Props {
  progress: JobProgress;
  filename: string;
}

export default function ProgressCard({ progress, filename }: Props) {
  const pct = progress.progress;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <p className="font-medium text-gray-800 truncate max-w-xs">{filename}</p>
        <span className={clsx("text-xs font-semibold px-2.5 py-1 rounded-full", STATUS_COLOR[progress.status])}>
          {STATUS_LABEL[progress.status]}
        </span>
      </div>

      {/* Progress bar */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs text-gray-500">
          <span>{progress.current_step || STATUS_LABEL[progress.status]}</span>
          <span>{pct}%</span>
        </div>
        <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={clsx(
              "h-full rounded-full transition-all duration-500",
              progress.status === "ERROR" ? "bg-red-400" :
              progress.status === "DONE" ? "bg-green-500" : "bg-brand-500"
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Block stats */}
      {progress.total_blocks > 0 && (
        <p className="text-xs text-gray-400">
          블록 {progress.translated_blocks} / {progress.total_blocks} 번역 완료
        </p>
      )}

      {/* Error */}
      {progress.status === "ERROR" && progress.error_message && (
        <p className="text-sm text-red-500">{progress.error_message}</p>
      )}
    </div>
  );
}
