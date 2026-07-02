import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        accent: "#6366f1",
      },
    },
  },
  plugins: [],
};

export default config;
