/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          dark: '#070b14',
          card: 'rgba(10, 20, 38, 0.75)',
          border: 'rgba(0, 240, 255, 0.25)',
          accent: '#00f0ff',
          neon: '#00e5ff',
          warning: '#ffb703',
          danger: '#ff3366',
          success: '#00f59b'
        }
      },
      boxShadow: {
        'cyber-glow': '0 0 15px rgba(0, 240, 255, 0.3)',
        'danger-glow': '0 0 15px rgba(255, 51, 102, 0.4)',
        'warning-glow': '0 0 15px rgba(255, 183, 3, 0.4)',
      }
    },
  },
  plugins: [],
}
