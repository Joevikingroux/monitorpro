/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        'n10-teal': '#2dd4bf',
        'n10-teal-hover': '#14b8a6',
        'n10-black': '#000000',
        'n10-surface': '#050a12',
        'n10-card': 'rgba(10,18,32,0.7)',
        'n10-text': 'rgb(148,163,184)',
        'n10-heading': 'rgb(224,247,250)',
        'n10-muted': 'rgb(100,116,139)',
        'n10-elevated': '#0d1520',
      },
      fontFamily: {
        heading: ['Space Grotesk', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        'n10': '12px',
      },
    },
  },
  plugins: [],
}
