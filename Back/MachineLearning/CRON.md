# cron / Task Scheduler — 정기 작업 등록

> W1F — `compute_impression_outcomes.py` 매일 자정 실행 등록 가이드.

`compute_impression_outcomes.py` 는 idempotent (`ON CONFLICT DO NOTHING`) 이라
중복 실행은 안전하다. 호출 빈도는 *매일 1회*면 충분 (5/20/60 거래일 horizon 모두 처리).

---

## 환경변수

```
CAPSTONE_ROOT      = E:\Capstone Data\project_data        # DuckDB 가 있는 루트
DUCKDB_PATH        = ${CAPSTONE_ROOT}\db\market_data.duckdb
EVENTS_PG_URL      = postgresql://USER:PASS@HOST:5432/wp_capstone
```

PG 연결 실패 시 exit code 2, DuckDB 부재 시 exit 1, 정상 0.

---

## Windows — Task Scheduler

```powershell
# 매일 03:00 KST 실행. 운영 PC 가 켜져 있어야 함.
schtasks /Create `
  /TN "events_outcomes_daily" `
  /TR "E:\Capstone Data\venv\Scripts\python.exe E:\Capstone Data\WP_Capstone-main\Back\MachineLearning\compute_impression_outcomes.py" `
  /SC DAILY /ST 03:00 /F
```

수동 실행:
```powershell
schtasks /Run /TN "events_outcomes_daily"
```

확인:
```powershell
schtasks /Query /TN "events_outcomes_daily" /V /FO LIST
```

제거:
```powershell
schtasks /Delete /TN "events_outcomes_daily" /F
```

---

## Linux / WSL / Docker — cron

`/etc/cron.d/events_outcomes_daily`:

```cron
# m h dom mon dow user command
0 3 * * * appuser cd /app/Back/MachineLearning && /opt/venv/bin/python compute_impression_outcomes.py >> /var/log/events_outcomes.log 2>&1
```

또는 사용자 crontab (`crontab -e`):

```cron
0 3 * * * cd /app/Back/MachineLearning && /opt/venv/bin/python compute_impression_outcomes.py
```

---

## 옵션 — 일부 horizon 만

```bash
python compute_impression_outcomes.py --horizons 5 20    # 60d 는 별도 처리
python compute_impression_outcomes.py --dry-run          # 적재 없이 미리보기
```

`--dry-run` 은 첫 3건만 stdout 으로 노출. 운영 PG 변경 0.

---

## 모니터링

- 로그: 실행마다 stdout `[HH:MM:SS] horizon=N: pending X` + `→ ready to insert: Y`.
- 누적 outcome 수: `SELECT outcome_horizon_days, COUNT(*) FROM impression_outcomes GROUP BY 1`.
- 적재 지연 점검: 가장 오래된 *미적재* impression 의 `shown_at` 이 cutoff(`horizon × 1.5 + 5` 일) 이내인지.

---

## 차기 사이클 진화 계획

- W7 A/B: outcomes 가 비교군 평가의 *유일한 라이브 신호*. cron 누락 시 평가 불가.
- 백필: 과거 impression 에 대한 outcomes 가 부족하면 같은 스크립트를 *수동 1회* 실행으로 일괄 채움.
- 다른 horizon 추가: `--horizons 10 30` 등 자유 조합. 새 horizon 은 자동으로 *별도 행* 으로 적재됨.
