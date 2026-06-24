"use client";
import { useState } from "react";
import UploadZone from "@/components/UploadZone";
import JobList from "@/components/JobList";

interface JobEntry {
  jobId: string;
  filename: string;
}

export default function Home() {
  const [jobs, setJobs] = useState<JobEntry[]>([]);

  function handleJobCreated(jobId: string, filename: string) {
    setJobs((prev) => [{ jobId, filename }, ...prev]);
  }

  function handleRemove(jobId: string) {
    setJobs((prev) => prev.filter((j) => j.jobId !== jobId));
  }

  return (
    <main className="min-h-screen flex flex-col items-center px-4 py-14 gap-10">
      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold text-gray-900">문서 번역 에이전트</h1>
        <p className="text-gray-500">PDF · HWP · DOCX 문서를 AI가 문맥 번역합니다</p>
      </div>

      {/* Upload */}
      <div className="w-full max-w-2xl">
        <UploadZone onJobCreated={handleJobCreated} />
      </div>

      {/* Job list */}
      <JobList jobs={jobs} onRemove={handleRemove} />
    </main>
  );
}
