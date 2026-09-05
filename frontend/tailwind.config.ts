import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: '#14171A',
        surface: '#1E2226',
        border: '#2C3136',
        'text-primary': '#E8EAED',
        'text-muted': '#8B9198',
        risk: {
          critical: '#E5484D',
          high: '#F0883E',
          medium: '#E8C547',
          low: '#3FB950',
        },
        accent: '#5B8DEF',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      borderRadius: {
        panel: '6px',
        badge: '4px',
      },
    },
  },
  plugins: [],
};

export default config;