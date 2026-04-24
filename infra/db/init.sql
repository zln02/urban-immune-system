-- Urban Immune System — TimescaleDB 초기화
-- docker-compose 기동 시 자동 실행됨

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 3-Layer 원시 신호 테이블
CREATE TABLE IF NOT EXISTS layer_signals (
    id         BIGSERIAL,
    time       TIMESTAMPTZ    NOT NULL,
    layer      VARCHAR(10)    NOT NULL,   -- 'otc' | 'wastewater' | 'search' | 'weather'
    region     VARCHAR(50)    NOT NULL,
    value      DOUBLE PRECISION NOT NULL, -- Min-Max 정규화 (0~100)
    raw_value  DOUBLE PRECISION,
    source     VARCHAR(100),
    PRIMARY KEY (id, time)
);

SELECT create_hypertable('layer_signals', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS ix_layer_signals_layer_region ON layer_signals (layer, region, time DESC);

-- 융합 리스크 점수
CREATE TABLE IF NOT EXISTS risk_scores (
    id               BIGSERIAL,
    time             TIMESTAMPTZ    NOT NULL,
    region           VARCHAR(50)    NOT NULL,
    composite_score  DOUBLE PRECISION NOT NULL,
    l1_score         DOUBLE PRECISION,
    l2_score         DOUBLE PRECISION,
    l3_score         DOUBLE PRECISION,
    alert_level      VARCHAR(20),            -- 'GREEN' | 'YELLOW' | 'RED'
    created_at       TIMESTAMPTZ    DEFAULT NOW(),
    PRIMARY KEY (id, time)
);

SELECT create_hypertable('risk_scores', 'time', if_not_exists => TRUE);

-- LLM 경보 리포트
CREATE TABLE IF NOT EXISTS alert_reports (
    id               BIGSERIAL PRIMARY KEY,
    time             TIMESTAMPTZ    NOT NULL,
    region           VARCHAR(50)    NOT NULL,
    alert_level      VARCHAR(20)    NOT NULL,
    summary          TEXT           NOT NULL,
    recommendations  TEXT,
    model_used       VARCHAR(50),
    created_at       TIMESTAMPTZ    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_alert_reports_time ON alert_reports (time DESC);

-- KCDC 감염병 확진 통계 (확진자 수 ground truth)
CREATE TABLE IF NOT EXISTS confirmed_cases (
    id          BIGSERIAL,
    time        TIMESTAMPTZ NOT NULL,
    region      VARCHAR(40) NOT NULL,
    disease     VARCHAR(40) NOT NULL,
    case_count  INTEGER     NOT NULL,
    per_100k    DOUBLE PRECISION,
    source      VARCHAR(40) DEFAULT 'KCDC',
    PRIMARY KEY (id, time)
);

SELECT create_hypertable('confirmed_cases', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_cc_region_time ON confirmed_cases (region, time DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uix_cc_time_region_disease ON confirmed_cases (time, region, disease);

-- 연속 집계 (TimescaleDB 자동 롤업) — 주간 평균
CREATE MATERIALIZED VIEW IF NOT EXISTS layer_signals_weekly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 week', time) AS week,
    layer,
    region,
    AVG(value)   AS avg_value,
    MAX(value)   AS max_value,
    COUNT(*)     AS data_points
FROM layer_signals
GROUP BY week, layer, region
WITH NO DATA;
