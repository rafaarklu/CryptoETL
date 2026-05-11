-- Explicação sobre para que serve cada tabela
-- Tabelas 1 e 2 são o que chegou da API, sem alteração. Se algo der errado no ETL, 
-- os dados brutos ainda estão lá e você reprocessa sem precisar chamar a API de novo.

-- Tabela 3 é o resultado do trabalho do pipeline. O Airflow lê as tabelas 1 e 2, faz as transformações
-- (alinha datas, converte moeda, calcula métricas) e grava o resultado consolidado aqui.

CREATE TABLE IF NOT EXISTS bcb_indicators (
    id              SERIAL          PRIMARY KEY,
    reference_date  DATE            NOT NULL,
    indicator       VARCHAR(10)     NOT NULL,   -- 'dolar' | 'selic' | 'ipca'
    valor           NUMERIC(15, 8)  NOT NULL,
    ingested_at     TIMESTAMP       NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_bcb_indicator_date UNIQUE (indicator, reference_date)
);



CREATE TABLE IF NOT EXISTS crypto_market (
    id              SERIAL          PRIMARY KEY,
    coin_id         VARCHAR(50)     NOT NULL,   -- 'bitcoin' | 'ethereum' | 'solana' | 'binancecoin'
    reference_date  DATE            NOT NULL,
    price_usd       NUMERIC(20, 8),
    market_cap_usd  NUMERIC(30, 2),
    volume_24h_usd  NUMERIC(30, 2),
    ingested_at     TIMESTAMP       NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_crypto_coin_date UNIQUE (coin_id, reference_date)
);


CREATE TABLE IF NOT EXISTS daily_consolidated (
    id                  SERIAL          PRIMARY KEY,
    reference_date      DATE            NOT NULL,
    coin_id             VARCHAR(50)     NOT NULL,

    -- cripto
    price_usd           NUMERIC(20, 8),
    price_brl           NUMERIC(20, 8),   -- price_usd * dolar_brl do dia
    market_cap_usd      NUMERIC(30, 2),
    volume_24h_usd      NUMERIC(30, 2),
    pct_change_1d       NUMERIC(10, 4),   -- variação % vs dia anterior
    volatility_7d       NUMERIC(10, 4),   -- desvio padrão rolling 7 dias

    -- macro BCB
    dolar_brl           NUMERIC(10, 6),
    selic_daily_rate    NUMERIC(12, 8),   -- taxa % ao dia (raw)
    selic_annual_rate   NUMERIC(10, 6),   -- ((1 + selic/100)^252 - 1) * 100
    ipca_monthly        NUMERIC(8, 4),    -- forward fill do valor mensal

    created_at          TIMESTAMP       NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_consolidated_coin_date UNIQUE (coin_id, reference_date)
);


CREATE TABLE IF NOT EXISTS pipeline_run_log (
    id              SERIAL          PRIMARY KEY,
    dag_id          VARCHAR(100)    NOT NULL,
    task_id         VARCHAR(100)    NOT NULL,
    source          VARCHAR(20),               -- 'coingecko' | 'bcb'
    status          VARCHAR(20)     NOT NULL,  -- 'success' | 'failed' | 'skipped'
    rows_inserted   INT             DEFAULT 0,
    error_message   TEXT,
    started_at      TIMESTAMP       NOT NULL,
    finished_at     TIMESTAMP
);

CREATE DATABASE airflow_db OWNER etl_user;

