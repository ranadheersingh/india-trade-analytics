import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#eef5fc",
          100: "#d4e6f7",
          200: "#a8cdef",
          300: "#7cb4e7",
          400: "#509bdf",
          500: "#2482d7",
          600: "#1f4e78",
          700: "#193e60",
          800: "#132f48",
          900: "#0c1f30",
        },
      },
    },
  },
  plugins: [],
};
export default config;
