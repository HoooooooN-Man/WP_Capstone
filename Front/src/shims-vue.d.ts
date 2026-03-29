declare module '*.vue' {
  import type { DefineComponent } from 'vue';
  const component: DefineComponent<{}, {}, any>;
  export default component;
}

declare module '*.css';

declare module '*.scss';

declare module '*.sass';

declare module 'swiper/css';

declare module 'swiper/css/effect-cards';
