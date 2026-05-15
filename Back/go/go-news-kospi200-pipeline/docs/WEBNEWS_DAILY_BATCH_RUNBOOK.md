# Webnews Daily Batch Runbook

## 1. 목적

Webnews 파이프라인은 서비스 화면에 표시할 뉴스 current JSON 세트를 생성하는 RSS-only 뉴스 배치 시스템이다.

기존 상시 worker 및 15분 주기 구조를 제거하고, 매일 장 시작 직전 1회 실행하는 구조로 단순화한다.

## 2. 실행 기준

- 실행 시각: 매일 08:50 KST
- display_date: 실행 당일
- 수집 window: 전일 09:00:00 ~ 당일 08:59:59
- 카테고리:
  - korea
  - world
  - business
  - science_tech
  - policy_finance
  - industry_ai
- 기본 Top N: 카테고리당 10개

## 3. 실행 흐름

```text
build_webnews_bins.sh
→ webnews_prune --phase before
→ webnews_scheduler --display-date YYYY-MM-DD
→ webnews_collector --once --idle-timeout 10s
→ webnews_enricher --once --idle-timeout 10s
→ webnews_finalizer --display-date YYYY-MM-DD
→ webnews_publish --display-date YYYY-MM-DD
→ webnews_prune --phase after