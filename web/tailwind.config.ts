import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: "#0F1729",
          navy: "#1A2340",
          amber: "#E8960C",
          "amber-light": "#FFF3DD",
          teal: "#1BA89C",
          "teal-light": "#E6F7F5",
          muted: "#6E7787",
          surface: "#F6F7F9",
          border: "#E2E5EB",
          card: "#FFFFFF",
        },
      },
      fontFamily: {
        display: ["Syne", "sans-serif"],
        body: ["DM Sans", "sans-serif"],
        mono: ["DM Mono", "monospace"],
      },
      boxShadow: {
        "card": "0 1px 3px rgba(15, 23, 41, 0.04), 0 1px 2px rgba(15, 23, 41, 0.06)",
        "card-hover": "0 4px 12px rgba(15, 23, 41, 0.08), 0 1px 3px rgba(15, 23, 41, 0.06)",
        "elevated": "0 8px 24px rgba(15, 23, 41, 0.08)",
      },
    },
  },
  plugins: [],
};
export default config;
