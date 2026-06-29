import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0a0a0f',
        card: '#12121a',
        border: '#1e1e2e',
        green: { DEFAULT: '#00d4a0', dark: '#009e77' },
        red: { DEFAULT: '#ff4757', dark: '#cc3344' },
        blue: { DEFAULT: '#4a9eff', dark: '#2277cc' },
        text: { DEFAULT: '#e8e8f0', muted: '#6b6b8a' },
      },
      fontFamily: { mono: ['JetBrains Mono', 'Fira Code', 'monospace'] },
    },
  },
  plugins: [],
};

export default config;
