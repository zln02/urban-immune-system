import type { ReactNode } from "react";

export const metadata = {
  title: "Urban Immune System",
  description: "Urban risk intelligence dashboard",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
