# PrimeVue 커스텀 테마

> UX 사이클 W1 시드. 사용자 디자인 결정 후 토스 스타일 커스텀 preset 박제.

## 현재 상태 (W1 시드)

PrimeVue `@primevue/themes/aura` preset 을 그대로 사용 (`main.ts` 참고).
디자인 토큰 결정 후 본 디렉토리에 커스텀 preset 추가:

```ts
// e.g. themes/toss-preset.ts
import { definePreset } from '@primevue/themes';
import Aura from '@primevue/themes/aura';

export default definePreset(Aura, {
  semantic: {
    primary: {
      50:  'var(--color-primary-50)',
      // ...
      950: 'var(--color-primary-950)',
    },
    // ...
  },
});
```

## 정책 (CLAUDE.md §3 PrimeVue 외 컴포넌트 라이브러리 도입 금지)

- 12주 내내 PrimeVue + `@primevue/themes` 만 사용.
- 토큰 값은 `src/styles/design-tokens.css` 가 single source — PrimeVue preset 은 CSS 변수 참조.
- 라이브러리 메이저 업데이트 금지 (`package.json` 핀).

## 적용 위치

`src/main.ts` 의 `app.use(PrimeVue, { theme: { preset: ... } })`.
