/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0b0e12',
        panel: '#12161b',
        card: '#171c22',
        accent: {
          from: '#f7941d',
          to: '#ef5a1c',
        },
      },
    },
  },
  plugins: [],
}
