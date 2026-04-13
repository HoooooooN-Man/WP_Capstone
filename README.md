# WP_Capstone

캡스톤 프로젝트 통합 저장소입니다.

## 구조
- Front: Vue 프론트엔드
- Back: Django 백엔드
- Learning: 딥러닝 실험 및 모델 코드

- Styling: Tailwind CSS
- Icons: lucide-vue-next

## 실행 방법

### Front
```bash
cd Front
npm install
npm run dev

#2026-04-14
* `AuthWallet.vue`: 초기 로그인 화면. 3D 자물쇠 해제 및 지갑이 화면 아래로 사라지는 애니메이션 담당.
* `CardWallet.vue`: 대시보드 하단 네비게이션 역할을 하는 활짝 펼쳐진 지갑. 4개의 카드 슬롯 관리.
* `ProfileView.vue`: 기본 화면. 사용자 정보와 자산이 꽉 찬 형태로 나타나는 메인 신분증 대시보드.
* `FeedView.vue`, `CompanyView.vue`, `PortfolioView.vue`: 하단 카드 선택 시 부드럽게 전환되는 서브 화면들.