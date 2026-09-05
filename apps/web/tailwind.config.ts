import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: {
          bg: "#0b0d10",
          panel: "#111418",
          panel2: "#161a1f",
          border: "#23272e",
          text: "#e6e8eb",
          muted: "#8a919c",
        },
        accent: {
          DEFAULT: "#3b82f6",
          dim: "#1d4ed8",
        },
        sev: {
          critical: "#ef4444",
          high: "#f97316",
          medium: "#eab308",
          low: "#64748b",
          info: "#3b82f6",
        },
      },
      fontFamily: {
        sans: ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "Inter", "sans-serif"],
        mono: ["SF Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        DEFAULT: "4px",
        sm: "2px",
        md: "6px",
      },
    },
  },
  plugins: [],
};
export default config;
