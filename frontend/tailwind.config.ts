import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: '1rem',
      screens: { '2xl': '1280px' },
    },
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['"Plus Jakarta Sans"', 'Inter', 'sans-serif'],
      },
      colors: {
        // Palette CI MINSAN
        ci: {
          green: '#009E60',     // vert drapeau ivoirien
          orange: '#FF7F00',    // orange drapeau ivoirien
          deep: '#0B3D2E',
          night: '#0F172A',
          surface: '#F8FAFC',
          mute: '#64748B',
        },
        risk: {
          low: '#10B981',
          moderate: '#F59E0B',
          high: '#EF4444',
          critical: '#7F1D1D',
        },
      },
      boxShadow: {
        card: '0 1px 0 rgba(15,23,42,0.04), 0 12px 32px -16px rgba(15,23,42,0.18)',
        glow: '0 0 0 4px rgba(16, 185, 129, 0.18)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(circle at top, var(--tw-gradient-stops))',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'pulse-dot': {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.7' },
          '50%': { transform: 'scale(1.4)', opacity: '1' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.4s ease-out both',
        'pulse-dot': 'pulse-dot 1.6s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};

export default config;
