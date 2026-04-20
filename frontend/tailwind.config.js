/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#16211f",
        pine: "#1d6f5f",
        coral: "#b64b3a",
        mist: "#f5f7f6"
      }
    }
  },
  plugins: []
};

