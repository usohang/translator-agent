"use client";
import { useState, useRef, DragEvent } from "react";
import { uploadFile } from "@/lib/api";

interface Props {
  onJobCreated: (jobId: string, filename: string) => void;
}

const ACCEPT = ".pdf,.hwp,.hwpx,.docx";

export default function UploadZone({ onJobCreated }: Props) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    const file = files[0];
    setError("");
    setUploading(true);
    try {
      const { job_id, filename } = await uploadFile(file);
      onJobCreated(job_id, filename);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "업로드 중 오류가 발생했습니다.");
    } finally {
      setUploading(false);
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={`
        flex flex-col items-center justify-center gap-3
        border-2 border-dashed rounded-2xl p-12 cursor-pointer
        transition-colors duration-150
        ${dragging ? "border-brand-500 bg-brand-50" : "border-gray-300 hover:border-brand-500 hover:bg-gray-100"}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />

      {uploading ? (
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-gray-500">업로드 중...</span>
        </div>
      ) : (
        <>
          <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-base font-medium text-gray-700">파일을 드래그하거나 클릭하여 선택</p>
          <p className="text-sm text-gray-400">PDF · HWP · HWPX · DOCX (최대 50MB)</p>
        </>
      )}

      {error && <p className="text-sm text-red-500 mt-1">{error}</p>}
    </div>
  );
}
