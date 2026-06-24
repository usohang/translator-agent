"use client";
import { useEffect, useState } from "react";
import { JobProgress, streamJob, downloadUrl, deleteJob } from "@/lib/api";
import ProgressCard from "./ProgressCard";

interface Job {
  jobId: string;
  filename: string;
  progress: JobProgress;
}

interface Props {
  jobs: { jobId: string; filename: string }[];
  onRemove: (jobId: string) => void;
}

export default function JobList({ jobs, onRemove }: Props) {
  const [jobStates, setJobStates] = useState<Record<string, JobProgress>>({});

  useEffect(() => {
    const cleanups: (() => void)[] = [];

    for (const { jobId } of jobs) {
      if (jobStates[jobId]?.status === "DONE" || jobStates[jobId]?.status === "ERROR") continue;

      const stop = streamJob(
        jobId,
        (p) => setJobStates((prev) => ({ ...prev, [jobId]: p })),
        () => {},
        () => {},
      );
      cleanups.push(stop);
    }

    return () => cleanups.forEach((c) => c());
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobs.map((j) => j.jobId).join(",")]);

  if (jobs.length === 0) return null;

  return (
    <div className="space-y-3 w-full max-w-2xl">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">작업 목록</h2>
      {jobs.map(({ jobId, filename }) => {
        const p = jobStates[jobId];
        if (!p) return null;
        return (
          <div key={jobId} className="relative">
            <ProgressCard progress={p} filename={filename} />

            <div className="flex gap-2 mt-2 justify-end">
              {p.status === "DONE" && (
                <a
                  href={downloadUrl(jobId)}
                  download
                  className="text-sm px-4 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg transition-colors"
                >
                  DOCX 다운로드
                </a>
              )}
              <button
                onClick={async () => {
                  await deleteJob(jobId);
                  onRemove(jobId);
                }}
                className="text-sm px-3 py-1.5 text-gray-500 hover:text-red-500 transition-colors"
              >
                삭제
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
