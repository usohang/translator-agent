import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "번역 에이전트",
  description: "PDF·HWP·DOCX 문서를 Claude AI로 번역합니다",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="bg-gray-50 text-gray-900 antialiased">{children}</body>
    </html>
  );
}
