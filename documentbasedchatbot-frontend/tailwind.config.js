/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        theme: {
          base: '#1C1929',
          card: '#29253C',
          cardBorder: '#3D3753',
          accent: '#A855F7',
          accentDim: '#7C3AED',
          muted: '#B0A6DC',
          glow: 'rgba(168, 85, 247, 0.4)',
        },
      },
    },
  },
  plugins: [],
}
