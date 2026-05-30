/**
 * Foundry design tokens — Educto.
 * See docs/superpowers/specs/2026-05-28-foundry-ui-redesign-design.md
 */
module.exports = {
  content: [
    '../templates/**/*.html',
    '../../**/templates/**/*.html',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: {
          base:     '#0A0D12',
          panel:    '#11151C',
          elevated: '#181D27',
          hover:    '#1F2533',
          active:   '#283041',
        },
        border: {
          subtle: '#1F2533',
          strong: '#2D3648',
          accent: '#00B8D4',
        },
        text: {
          primary:   '#E6E9EF',
          secondary: '#8B95A7',
          muted:     '#5C6578',
          mono:      '#C8FFE9',
        },
        accent: {
          DEFAULT: '#00B8D4',
          hover:   '#00D4F2',
          muted:   '#003D47',
        },
        success: '#4ADE80',
        warning: '#FBBF24',
        danger:  '#F87171',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', '"JetBrains Mono"', 'monospace'],
      },
      fontSize: {
        'mono-data':  ['13px',  { lineHeight: '18px', fontWeight: '500' }],
        'mono-label': ['11px',  { lineHeight: '14px', fontWeight: '500', letterSpacing: '0.08em' }],
        'display':    ['32px',  { lineHeight: '36px', fontWeight: '600', letterSpacing: '-0.02em' }],
      },
      borderRadius: { DEFAULT: '2px', md: '4px' },
      spacing: { '4.5': '18px', '13': '52px', '15': '60px' },
      boxShadow: { overlay: '0 8px 24px rgba(0,0,0,0.5)' },
      transitionTimingFunction: { foundry: 'cubic-bezier(0.2, 0, 0.2, 1)' },
      transitionDuration: { '120': '120ms' },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('@tailwindcss/forms'),
  ],
}
