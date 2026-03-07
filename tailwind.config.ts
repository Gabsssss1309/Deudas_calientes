import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        unergy: {
          purple: "#915BD8",
          "deep-purple": "#2C2039",
          cream: "#FDFAF7",
          "solar-yellow": "#F6FF72",
        },
        semaforo: {
          verde: "#3FB950",
          amarillo: "#F6FF72",
          rojo: "#F85149",
        },
      },
      fontFamily: {
        body: ["var(--font-lato)", "Open Sans", "sans-serif"],
        display: ["var(--font-poppins)", "Montserrat", "sans-serif"],
      },
      borderRadius: {
        card: "12px",
        button: "8px",
      },
    },
  },
  plugins: [],
};
export default config;
