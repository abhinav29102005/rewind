/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        serif: ['Newsreader', 'Georgia', 'serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
      colors: {
        ego: {
          bg: '#fcfbfa',
          dark: '#111111',
          card: '#ffffff',
          border: '#e8e6e1',
          muted: '#71717a',
          accent: '#2563eb',
          highlight: '#e0e7ff',
          court: '#1e392a',
        }
      },
      boxShadow: {
        'window': '0 20px 70px -10px rgba(0, 0, 0, 0.18), 0 1px 3px rgba(0,0,0,0.06)',
        'float': '0 30px 60px -12px rgba(0, 0, 0, 0.25), 0 18px 36px -18px rgba(0, 0, 0, 0.3)',
        'pill': '0 2px 8px rgba(0, 0, 0, 0.08)',
      }
    },
  },
  plugins: [],
}
