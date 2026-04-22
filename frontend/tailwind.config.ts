import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Pretendard GOV Variable",
          "Pretendard Variable",
          "Pretendard",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "system-ui",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "IBM Plex Mono", "ui-monospace", "monospace"],
      },
      colors: {
        background: "var(--bg)",
        foreground: "var(--text)",
        primary: {
          DEFAULT: "var(--accent)",
          foreground: "var(--text-inverse)",
        },
        muted: {
          DEFAULT: "var(--bg-sub)",
          foreground: "var(--text-secondary)",
        },
        border: "var(--border)",
        ring: "var(--focus)",
        risk: {
          safe: "var(--risk-safe)",
          caution: "var(--risk-caution)",
          warning: "var(--risk-warning)",
          alert: "var(--risk-alert)",
        },
        layer: {
          pharmacy: "var(--layer-pharmacy)",
          sewage: "var(--layer-sewage)",
          search: "var(--layer-search)",
        },
      },
      borderRadius: {
        sm: "var(--r-sm)",
        md: "var(--r-md)",
        lg: "var(--r-lg)",
        xl: "var(--r-xl)",
      },
    },
  },
  plugins: [],
};

export default config;
