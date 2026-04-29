import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Urban Immune System",
  description: "AI 기반 감염병 조기경보 시스템",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <Providers>
          <a href="#main-content" className="skip-link">메인 콘텐츠로 이동</a>
          <div id="main-content">{children}</div>
        </Providers>
      </body>
    </html>
  );
}
