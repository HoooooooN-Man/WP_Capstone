# Cron 등록 가이드 — 차차기 W6B

> 데이터 수집·점수 적재 자동화. 사용자 권고 — *manual 등록 + 가이드 문서*. 자동 등록
> 스크립트는 OS 별 분기 부담으로 작성 안 함.

## 운영 채널 (cron_runtime.py 자동)

매 cron 실행은 3 곳에 동시 기록:

1. `logs/cron_status.log` — 한 줄 append (START·OK·FAIL·sentinel 위치).
2. `logs/FAIL_<step>_<YYYYMMDD_HHMMSS>.flag` — *실패 시만* 생성. 사용자가 디렉토리
   모니터링. 다음 정상 run 후에도 자동 삭제 안 함 — *사후 확인 후 manual 삭제*.
3. DuckDB `cron_runs` 테이블 — 구조화. W2 대시보드·W6D roll-back trigger 입력.

## Windows Task Scheduler 등록 (사용자 환경 우선)

### 1. 수집 cron (collect_cron.py)

권장: **매일 18:00 KST** (KRX 장 마감 + 데이터 안정화 시간).

```
Program/script:  E:\Capstone Data\WP_Capstone-main\.venv\Scripts\python.exe
Arguments:       Back\MachineLearning\data_pipeline\collect_cron.py
Start in:        E:\Capstone Data\WP_Capstone-main
Schedule:        Daily at 18:00
환경변수:        KRX_ID, KRX_PW (등록 시 Task 의 Action → Environment 또는 시스템 env)
```

GUI 등록 절차:
1. `taskschd.msc` → Action → "Create Basic Task"
2. Name: `capstone-collect-daily`
3. Trigger: Daily, 18:00
4. Action: Start a program → 위 Program/script + Arguments + Start in
5. Finish 후 Properties → "Run whether user is logged on or not" 체크
6. Properties → Settings → "Stop the task if it runs longer than: 2 hours" (안전망)

### 2. 점수 적재 cron (W6C 에서 추가 예정)

```
Program:    py.exe
Arguments:  Back\MachineLearning\precompute_scores_v11_cron.py --variant a_prime
Schedule:   Daily at 19:30 (수집 cron 완료 후 충분 시간)
```

## Linux/Mac cron (다른 환경 — 가이드만, 미검증)

```cron
# /etc/cron.d/capstone   또는   crontab -e
KRX_ID=...
KRX_PW=...
DUCKDB_PATH=/data/market_data.duckdb

# 매일 18:00 KST
0 18 * * * cd /path/to/WP_Capstone && \
    /path/to/python Back/MachineLearning/data_pipeline/collect_cron.py
```

## CI 환경 (GitHub Actions — 가이드만)

```yaml
name: collect-daily
on:
  schedule:
    - cron: '0 9 * * *'   # UTC = 18:00 KST
jobs:
  collect:
    runs-on: ubuntu-latest
    env:
      KRX_ID: ${{ secrets.KRX_ID }}
      KRX_PW: ${{ secrets.KRX_PW }}
    steps:
      - uses: actions/checkout@v4
      - run: python Back/MachineLearning/data_pipeline/collect_cron.py
```

## 실패 인지 patterns

운영자는 다음 셋 중 *최소 한 가지* 를 주기 점검:

1. **빠른 시각 점검**: `ls logs/FAIL_*.flag` (없으면 모두 OK).
2. **최근 로그 tail**: `Get-Content logs/cron_status.log -Tail 20` (PowerShell)
   또는 `tail -20 logs/cron_status.log` (POSIX).
3. **DuckDB 쿼리** (W2 대시보드 입력 형식):
   ```sql
   SELECT step, started_at, status, duration_sec, error_class
   FROM cron_runs
   WHERE started_at > now() - INTERVAL 3 DAYS
   ORDER BY started_at DESC;
   ```

## W6D Roll-back 알림 정책 (구현 완료 — rollback_monitor.py)

**트리거 조건:**
- 같은 step 의 *최근 3 연속 `failed`* (no_change·running 제외, status NOT IN 으로 필터).
- 다른 step 의 실패는 별개 trigger (precompute_scores 실패 ≠ collect_and_build 실패).

**동작 (사용자 권고 — 자동 swap 없음):**
- env 자동 변경 X (실패 원인 미해결 상태 자동 복귀 위험).
- 대신 3 채널 동시 알림:
  - `logs/ROLLBACK_<step>_<ts>.flag` sentinel — 복귀 절차 본문 박제.
  - `cron_status.log` 의 `ROLLBACK_ALERT` 한 줄.
  - DuckDB `rollback_events` 테이블 (event_id·step·triggered_at·threshold·reason
    ·resolved_at).

**Schedule (`rollback_check_cron.py`):**
```
Program:    py.exe
Arguments:  Back\MachineLearning\data_pipeline\rollback_check_cron.py
Schedule:   매 시간 정각 (수집·점수 cron 정시 후 빠른 인지)
```

**복귀 절차 (manual, sentinel 본문 명시):**
1. `logs/cron_status.log` + `logs/FAIL_<step>_*.flag` 로 실패 원인 점검.
2. 코드·데이터·환경 수정.
3. 정상 1회 run 으로 cron_runs.status='ok' 추가 (다음 trigger 평가 시 *failed 누적 끊김*).
4. (선택) `DEFAULT_MODEL_VERSION` env 수정 — resolve_version 이 새 default 사용.
5. ROLLBACK sentinel manual 삭제 + `rollback_events.resolved_at` UPDATE.

## 자격 관리 (보안)

- `KRX_ID`·`KRX_PW`·`DART_API_KEY` 는 **plaintext 코드 금지** (W6A 에서 fix 완료).
- 환경변수 또는 OS 시크릿 저장소 (Windows Credential Manager) 활용.
- 본 가이드를 git 에 올릴 때 *예시 자격 미포함* (위 KRX_ID=... 만 placeholder).
