import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: {
    default: "Urban Immune System — AI 감염병 조기경보",
    template: "%s | Urban Immune System",
  },
  description:
    "3-Layer 비의료 신호(약국 OTC · 하수 바이오마커 · 검색 트렌드) AI 교차검증 기반 감염병 조기경보 서비스",
  openGraph: {
    title: "Urban Immune System",
    description: "AI 기반 감염병 조기경보 서비스",
    locale: "ko_KR",
    type: "website",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#1F2D5B" },
    { media: "(prefers-color-scheme: dark)", color: "#0A0F1C" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body className="min-h-screen bg-background text-foreground antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
