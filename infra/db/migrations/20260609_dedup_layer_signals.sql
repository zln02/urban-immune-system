-- 마이그레이션: layer_signals 중복 제거 + UNIQUE 제약 추가
-- 실행 일자: 2026-06-09
-- 사유 (#79 P0): 운영 DB audit 결과 wastewater 1616 행 중복 발견 — PRIMARY KEY (id, time) 만으로는
--                중복 방지 불가 (id 가 BIGSERIAL 이므로 같은 (layer, region, time, pathogen) 다중 INSERT 가능).
-- 적용 환경: 운영 GCP VM 의 timescaledb 컨테이너.
-- 사전 작업 (운영 적용 전 반드시):
--   1. 백업: docker exec uis-timescaledb pg_dump -U uis_user urban_immune > backup_pre_dedup_$(date +%Y%m%d).sql
--   2. 트랜잭션 안에서 실행 (BEGIN/COMMIT) — 실패 시 ROLLBACK.
--   3. 운영 cron 임시 중지 (수집 잡 INSERT 동시성 회피).
-- 적용 명령 (운영 컨테이너 안):
--   docker exec -i uis-timescaledb psql -U uis_user -d urban_immune < 20260609_dedup_layer_signals.sql

BEGIN;

-- ① 중복 행 식별 + 가장 큰 id 1개만 남기고 삭제 (가장 최근 INSERT 보존).
WITH duplicates AS (
    SELECT id, time,
           ROW_NUMBER() OVER (
               PARTITION BY layer, region, time, pathogen
               ORDER BY id DESC
           ) AS rn
    FROM layer_signals
)
DELETE FROM layer_signals ls
USING duplicates d
WHERE ls.id = d.id
  AND ls.time = d.time
  AND d.rn > 1;

-- ② UNIQUE 제약 추가 — TimescaleDB hypertable 은 time(파티션 키) 포함 필수.
CREATE UNIQUE INDEX IF NOT EXISTS uix_layer_signals_logical
    ON layer_signals (layer, region, time, pathogen);

-- ③ 적용 후 검증 — 같은 (layer, region, time, pathogen) 의 행 수가 모두 1 인지.
DO $$
DECLARE
    dup_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO dup_count FROM (
        SELECT layer, region, time, pathogen, COUNT(*) AS n
        FROM layer_signals
        GROUP BY layer, region, time, pathogen
        HAVING COUNT(*) > 1
    ) sub;

    IF dup_count > 0 THEN
        RAISE EXCEPTION 'Dedup failed: % duplicate groups still present', dup_count;
    END IF;

    RAISE NOTICE 'Dedup verified: 0 duplicate groups remaining';
END $$;

COMMIT;

-- 사후 작업:
--   1. 운영 cron 재개.
--   2. 다음 24h 동안 wastewater INSERT 시 IntegrityError 안 나는지 모니터링.
--   3. backup_pre_dedup_*.sql 14일 보관 후 archive.
