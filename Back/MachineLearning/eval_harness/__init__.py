"""
eval_harness — Tier 1.2 (PRD §3.5.1 / 캡스톤 §3.2)

축약 평가 하네스. v9 모델 산출물에 대해:
  - 슬라이스 4개: time / sector / cap_size / regime
  - 메트릭 5개:  AUC, ECE, Sharpe, MDD, alpha vs KOSPI
  - HTML 리포트 1개 + JSON 리포트 1개

진입점: `python -m eval_harness.run_eval --model v9`.
CI 통합·full multi-objective 탐색은 캡스톤 범위 외 (Tier 3).
"""
