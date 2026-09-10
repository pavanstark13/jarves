import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: '#0b0c10', raised: '#131519', line: '#23262e' },
        gold: { DEFAULT: '#e3b23c', bright: '#f5cd6a', dim: '#7a6224' },
        up: '#3ecf8e',
        down: '#ff5c5c',
        muted: '#8a8f9c',
        paper: '#e9ebf0',
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
};

export default config;
