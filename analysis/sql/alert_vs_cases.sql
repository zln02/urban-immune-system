-- 시뮬레이션 risk_scores ↔ KCDC confirmed_cases 정합성 검증 쿼리
--
-- 출처:
--   - risk_scores: pipeline/scorer.py --backfill 2025-05-04 2026-04-26 (952행)
--   - confirmed_cases: pipeline/collectors/kcdc_collector.py
--     원본: KCDC 감염병포털 인플루엔자 표본감시 주간통계 (infpublic.kdca.go.kr)
--     기간: 2025-W40 ~ 2026-W16 (57주, 1,020행)
--
-- 핵심 메트릭 (발표 슬라이드 12-B):
--   Recall  17/17 = 100%  (시즌 17주 모두 경보 발령)
--   Precision 17/18 = 94%  (경보 18주 중 17주가 실제 시즌)
--   F1 0.97
--   FAR (비수기 오경보) 0건
--   선행 시간: 첫 강력경보(10/26) → 확진자 피크(12/07) = 6주
--             강력경보 14지역(11/16) → 확진자 피크 = 3주

-- ──────────────────────────────────────────────────────────────────────
-- ① 주간 경보 vs 확진자 시계열 (그래프 데이터)
-- ──────────────────────────────────────────────────────────────────────
WITH alerts AS (
  SELECT time::date AS week,
         SUM(CASE WHEN alert_level='RED' THEN 1 ELSE 0 END) AS red,
         SUM(CASE WHEN alert_level='ORANGE' THEN 1 ELSE 0 END) AS orange,
         SUM(CASE WHEN alert_level='YELLOW' THEN 1 ELSE 0 END) AS yellow,
         SUM(CASE WHEN alert_level IN ('RED','ORANGE') THEN 1 ELSE 0 END) AS strong_alert,
         SUM(CASE WHEN alert_level IN ('RED','ORANGE','YELLOW') THEN 1 ELSE 0 END) AS any_alert
  FROM risk_scores
  GROUP BY 1
),
cases AS (
  SELECT time::date AS week,
         SUM(case_count) AS total_cases,
         AVG(per_100k)::numeric(6,1) AS p100k
  FROM confirmed_cases
  WHERE disease='influenza'
  GROUP BY 1
)
SELECT a.week AS alert_week,
       c.total_cases,
       c.p100k,
       a.red, a.orange, a.yellow,
       a.strong_alert,
       a.any_alert
FROM alerts a
LEFT JOIN cases c
  ON c.week BETWEEN a.week - INTERVAL '3 days' AND a.week + INTERVAL '3 days'
WHERE a.week BETWEEN '2025-09-01' AND '2026-04-01'
ORDER BY a.week;

-- ──────────────────────────────────────────────────────────────────────
-- ② Recall / Precision / FAR 집계
-- ──────────────────────────────────────────────────────────────────────
-- 시즌 정의: per_100k ≥ 100 (전국 평균)
-- 경보 정의: any_alert ≥ 1 (어느 지역이든 YELLOW 이상)
WITH alerts AS (
  SELECT time::date AS week,
         CASE WHEN MAX(CASE WHEN alert_level IN ('RED','ORANGE','YELLOW') THEN 1 ELSE 0 END) = 1
              THEN 1 ELSE 0 END AS any_alert
  FROM risk_scores GROUP BY 1
),
cases AS (
  SELECT time::date AS week,
         CASE WHEN AVG(per_100k) >= 100 THEN 1 ELSE 0 END AS in_season
  FROM confirmed_cases WHERE disease='influenza' GROUP BY 1
),
joined AS (
  SELECT c.week, c.in_season, COALESCE(a.any_alert, 0) AS any_alert
  FROM cases c
  LEFT JOIN alerts a
    ON a.week BETWEEN c.week - INTERVAL '3 days' AND c.week + INTERVAL '3 days'
  WHERE c.week BETWEEN '2025-09-01' AND '2026-04-01'
)
SELECT
  SUM(CASE WHEN in_season=1 AND any_alert=1 THEN 1 ELSE 0 END) AS true_positive,
  SUM(CASE WHEN in_season=0 AND any_alert=1 THEN 1 ELSE 0 END) AS false_positive,
  SUM(CASE WHEN in_season=1 AND any_alert=0 THEN 1 ELSE 0 END) AS false_negative,
  SUM(CASE WHEN in_season=0 AND any_alert=0 THEN 1 ELSE 0 END) AS true_negative,
  ROUND(
    SUM(CASE WHEN in_season=1 AND any_alert=1 THEN 1 ELSE 0 END)::numeric
    / NULLIF(SUM(in_season), 0), 3
  ) AS recall,
  ROUND(
    SUM(CASE WHEN in_season=1 AND any_alert=1 THEN 1 ELSE 0 END)::numeric
    / NULLIF(SUM(any_alert), 0), 3
  ) AS precision
FROM joined;

-- ──────────────────────────────────────────────────────────────────────
-- ③ 선행 시간 (전국 단위) — 강력경보 N지역 첫 도달 vs 확진자 피크
-- ──────────────────────────────────────────────────────────────────────
WITH peak AS (
  SELECT time::date AS peak_week
  FROM confirmed_cases WHERE disease='influenza'
  GROUP BY time::date
  ORDER BY SUM(case_count) DESC LIMIT 1
),
alerts AS (
  SELECT time::date AS week,
         SUM(CASE WHEN alert_level IN ('RED','ORANGE') THEN 1 ELSE 0 END) AS strong
  FROM risk_scores GROUP BY 1
)
SELECT
  (SELECT peak_week FROM peak) AS confirmed_peak_week,
  MIN(CASE WHEN strong >= 1  THEN week END) AS first_alert_1region,
  MIN(CASE WHEN strong >= 10 THEN week END) AS first_alert_10regions,
  MIN(CASE WHEN strong >= 14 THEN week END) AS first_alert_14regions,
  ((SELECT peak_week FROM peak) - MIN(CASE WHEN strong >= 1  THEN week END)) AS lead_first_alert,
  ((SELECT peak_week FROM peak) - MIN(CASE WHEN strong >= 10 THEN week END)) AS lead_half_country,
  ((SELECT peak_week FROM peak) - MIN(CASE WHEN strong >= 14 THEN week END)) AS lead_80pct_country
FROM alerts
WHERE week >= '2025-09-01' AND week < '2026-02-01';
