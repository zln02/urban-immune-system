# External Data Source — Expected Lag Policy

> 마지막 갱신: 2026-05-14
> 근거: PHASE B 데이터 신선도 진단 (2026-05-14)

## Expected Lag per Source

| Source                  | Layer      | Expected lag | Cadence              |
|-------------------------|------------|--------------|----------------------|
| naver_shopping_insight  | L1 OTC     | T-2 days     | Daily (T-2 publish)  |
| naver_datalab           | L3 search  | T-2 days     | Daily (T-2 publish)  |
| kowas (covid/influenza/norovirus) | L2 sewage | T-7~10 days | Weekly (Tue PDF) |
| kma_temperature         | AUX        | T-0          | Hourly               |

## Operational Semantics

- **Within threshold**: nominal operation. Scheduler healthy, collector pipeline healthy.
- **Beyond threshold**: collector failure. Investigate `db_writer._pool` stale loop, API quota, or PDF parsing error.

## Reference Incident

- **2026-04-26 → 2026-05-13** (17일 silent fail) — `db_writer._pool` event-loop binding bug. Fix: `pipeline/collectors/db_writer.py` stale pool detection (commit 74d5015).
- Backfill: `naver_backfill.run_backfill(weeks=N)` for L1/L3, manual KOWAS PDF download for L2.

## Monitoring (TODO)

- `/api/v1/health` 확장: 각 source max(time) 노출
- Alert if `(NOW - max(time)) > expected_lag * 1.5`
