// themes/wp-preset.ts — UX 사이클 W1 확정
//
// PrimeVue 4.4.1 Aura preset 위 wp 프로젝트 색 덮어쓰기.
// design-tokens.css 의 --color-primary-* 와 일치 (Radix Indigo).
// 검토 결과 (design-system-guide.md): Indigo 교체, 다크 미포함, Aura 기본 컴포넌트 유지.

import { definePreset } from '@primevue/themes';
import Aura from '@primevue/themes/aura';

export const WpPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50:  '#eef2ff',
      100: '#e0e7ff',
      200: '#c7d2fe',
      300: '#a5b4fc',
      400: '#818cf8',
      500: '#6366f1',
      600: '#4f46e5',
      700: '#4338ca',
      800: '#3730a3',
      900: '#312e81',
      950: '#1e1b4b',
    },
    colorScheme: {
      light: {
        surface: {
          0:   '#ffffff',
          50:  '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
        primary: {
          color: '{primary.600}',
          contrastColor: '#ffffff',
          hoverColor: '{primary.700}',
          activeColor: '{primary.800}',
        },
        formField: {
          background: '#ffffff',
          borderColor: '{surface.300}',
          hoverBorderColor: '{surface.400}',
          focusBorderColor: '{primary.500}',
          color: '{surface.900}',
          placeholderColor: '{surface.400}',
        },
        text: {
          color: '{surface.900}',
          mutedColor: '{surface.600}',
        },
        content: {
          background: '#ffffff',
          borderColor: '{surface.200}',
          color: '{surface.900}',
        },
      },
      // dark: 다음 사이클 후보
    },
    borderRadius: {
      none: '0',
      xs: '0.25rem',
      sm: '0.5rem',
      md: '0.75rem',
      lg: '1rem',
      xl: '1.5rem',
    },
    focusRing: {
      width: '3px',
      style: 'solid',
      color: '{primary.500}',
      offset: '2px',
    },
  },
});
