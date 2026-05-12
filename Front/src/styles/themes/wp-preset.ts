// themes/wp-preset.ts — Claude 초안 (본인 검토 대기)
//
// PrimeVue 4.4.1 Aura preset 위에 wp 프로젝트 색 덮어쓰기.
// design-tokens.css의 --color-primary-* 와 일치.
//
// 검토 시 짚을 점:
// 1. semantic.primary.500 이 #0ea5e9 — design-tokens.css 와 동기. 변경 시 양쪽 다.
// 2. colorScheme.light.surface.50~950 은 neutral 토큰 매핑. 다크모드 토큰 미작성 (다음 사이클).
// 3. components.button.colorScheme.* 등 컴포넌트별 세부는 기본 Aura 유지. 필요 시 추가.

import { definePreset } from '@primevue/themes';
import Aura from '@primevue/themes/aura';

export const WpPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50:  '#f0f9ff',
      100: '#e0f2fe',
      200: '#bae6fd',
      300: '#7dd3fc',
      400: '#38bdf8',
      500: '#0ea5e9',
      600: '#0284c7',
      700: '#0369a1',
      800: '#075985',
      900: '#0c4a6e',
      950: '#082f49',
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
