export default {
  content: [
  './index.html',
  './src/**/*.{js,ts,jsx,tsx}'
],
  theme: {
    extend: {
      colors: {
        albarka: {
          yellow: '#F5A623',
          'yellow-dark': '#E0950F',
          'yellow-soft': '#FEF6E7',
          black: '#1A1A1A',
          ink: '#3D3D3D',
          muted: '#6B7280',
          surface: '#FFFFFF',
          bg: '#F8F9FA',
          border: '#E9ECEF',
        },
        statut: {
          actif: '#1E9E62',
          risque: '#F5A623',
          'non-utilise': '#E8702A',
          'sans-qr': '#D0342C',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      boxShadow: {
        card: '0 1px 2px rgba(26, 26, 26, 0.05)',
        pop: '0 8px 24px rgba(26, 26, 26, 0.12)',
      },
    },
  },
  plugins: [],
}
