import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Urban Immune System",
  description: "AI 기반 감염병 조기경보 시스템",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="bg-gray-950 text-gray-100 min-h-screen">{children}</body>
    </html>
  );
}
