"""
Loader de dados para PostgreSQL.
"""
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from src.settings import DB_CONNECTION_STRING

logger = logging.getLogger(__name__)


class PostgresLoader:
    """Carrega dados em PostgreSQL com suporte a UPSERT."""
    
    def __init__(self, connection_string: str = DB_CONNECTION_STRING):
        """
        Inicializa o loader.
        
        Args:
            connection_string: String de conexão PostgreSQL
        """
        self.engine = create_engine(connection_string, echo=False)
        self.connection_string = connection_string
        logger.info(f"✓ PostgresLoader inicializado")
    
    def load_bcb_indicators(self, df: pd.DataFrame) -> int:
        """
        Carrega dados de indicadores BCB com UPSERT.
        
        Args:
            df: DataFrame com colunas [indicator, reference_date, valor]
        
        Returns:
            int: Número de registros inseridos/atualizados
        """
        logger.info("Iniciando carga de indicadores BCB...")
        
        # Adicionar timestamp de ingestão
        df = df.copy()
        df["ingested_at"] = datetime.now()
        
        try:
            # Use a transaction context manager provided by SQLAlchemy
            with self.engine.begin() as conn:
                for _, row in df.iterrows():
                    # UPSERT: INSERT ... ON CONFLICT DO UPDATE
                    query = text("""
                    INSERT INTO bcb_indicators (reference_date, indicator, valor, ingested_at)
                    VALUES (:ref_date, :indicator, :valor, :ingested_at)
                    ON CONFLICT (indicator, reference_date) DO UPDATE
                    SET valor = :valor, ingested_at = :ingested_at
                    """)
                    
                    conn.execute(query, {
                        "ref_date": row["reference_date"],
                        "indicator": row["indicator"],
                        "valor": float(row["valor"]),
                        "ingested_at": row["ingested_at"],
                    })
                
                # transaction is committed automatically by context manager
            
            logger.info(f"✓ Carga BCB concluída: {len(df)} registros processados")
            return len(df)
        
        except Exception as e:
            logger.error(f"✗ Erro ao carregar indicadores BCB: {str(e)}")
            raise
    
    def load_crypto_market(self, df: pd.DataFrame) -> int:
        """
        Carrega dados de mercado cripto com UPSERT.
        
        Args:
            df: DataFrame com colunas [coin_id, reference_date, price_usd, market_cap_usd, volume_24h_usd]
        
        Returns:
            int: Número de registros inseridos/atualizados
        """
        logger.info("Iniciando carga de dados de criptomoedas...")
        
        # Adicionar timestamp de ingestão
        df = df.copy()
        df["ingested_at"] = datetime.now()
        
        try:
            with self.engine.begin() as conn:
                for _, row in df.iterrows():
                    # UPSERT
                    query = text("""
                    INSERT INTO crypto_market (coin_id, reference_date, price_usd, market_cap_usd, volume_24h_usd, ingested_at)
                    VALUES (:coin_id, :ref_date, :price_usd, :market_cap_usd, :volume_24h_usd, :ingested_at)
                    ON CONFLICT (coin_id, reference_date) DO UPDATE
                    SET price_usd = :price_usd, market_cap_usd = :market_cap_usd, 
                        volume_24h_usd = :volume_24h_usd, ingested_at = :ingested_at
                    """)
                    
                    conn.execute(query, {
                        "coin_id": row["coin_id"],
                        "ref_date": row["reference_date"],
                        "price_usd": float(row["price_usd"]) if pd.notna(row["price_usd"]) else None,
                        "market_cap_usd": float(row["market_cap_usd"]) if pd.notna(row["market_cap_usd"]) else None,
                        "volume_24h_usd": float(row["volume_24h_usd"]) if pd.notna(row["volume_24h_usd"]) else None,
                        "ingested_at": row["ingested_at"],
                    })
                
                # transaction is committed automatically by context manager
            
            logger.info(f"✓ Carga cripto concluída: {len(df)} registros processados")
            return len(df)
        
        except Exception as e:
            logger.error(f"✗ Erro ao carregar dados cripto: {str(e)}")
            raise
    
    def consolidate_daily_table(self, start_date: str = None) -> int:
        """
        Consolida dados de bcb_indicators e crypto_market na tabela daily_consolidated.
        Executa SQL que faz o JOIN e cálculos necessários.
        
        Args:
            start_date: Data a partir da qual consolidar (formato YYYY-MM-DD). Se None, consolida tudo.
        
        Returns:
            int: Número de registros inseridos/atualizados
        """
        logger.info("Iniciando consolidação diária...")
        
        try:
            with self.engine.begin() as conn:
                # SQL de consolidação
                consolidation_sql = text("""
                WITH crypto_base AS (
                    SELECT
                        coin_id,
                        reference_date,
                        price_usd,
                        market_cap_usd,
                        volume_24h_usd,
                        LAG(price_usd) OVER (PARTITION BY coin_id ORDER BY reference_date) as prev_price
                    FROM crypto_market
                    WHERE (:start_date IS NULL OR reference_date >= :start_date)
                ),
                crypto_with_pct AS (
                    -- calcula a variação diária com base no preço anterior (evita aninhar window functions)
                    SELECT
                        coin_id,
                        reference_date,
                        price_usd,
                        market_cap_usd,
                        volume_24h_usd,
                        CASE WHEN prev_price IS NULL THEN NULL
                             ELSE ROUND(((price_usd - prev_price) / prev_price) * 100, 4)
                        END as pct_change_1d
                    FROM crypto_base
                ),
                crypto_with_vol AS (
                    -- calcula a volatilidade a partir da coluna pct_change_1d (sem LAG aninhado)
                    SELECT
                        coin_id,
                        reference_date,
                        price_usd,
                        market_cap_usd,
                        volume_24h_usd,
                        pct_change_1d,
                        ROUND(
                            STDDEV(pct_change_1d) OVER (PARTITION BY coin_id ORDER BY reference_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW),
                            4
                        ) as volatility_7d
                    FROM crypto_with_pct
                ),
                bcb_filled AS (
                    SELECT
                        c.reference_date,
                        COALESCE(
                            (
                                SELECT bi.valor
                                FROM bcb_indicators bi
                                WHERE bi.indicator = 'dolar'
                                  AND bi.reference_date <= c.reference_date
                                ORDER BY bi.reference_date DESC
                                LIMIT 1
                            ),
                            (
                                SELECT bi.valor
                                FROM bcb_indicators bi
                                WHERE bi.indicator = 'dolar'
                                ORDER BY bi.reference_date ASC
                                LIMIT 1
                            )
                        ) AS dolar_brl,
                        COALESCE(
                            (
                                SELECT bi.valor
                                FROM bcb_indicators bi
                                WHERE bi.indicator = 'selic'
                                  AND bi.reference_date <= c.reference_date
                                ORDER BY bi.reference_date DESC
                                LIMIT 1
                            ),
                            (
                                SELECT bi.valor
                                FROM bcb_indicators bi
                                WHERE bi.indicator = 'selic'
                                ORDER BY bi.reference_date ASC
                                LIMIT 1
                            )
                        ) AS selic_daily_rate,
                        COALESCE(
                            (
                                SELECT bi.valor
                                FROM bcb_indicators bi
                                WHERE bi.indicator = 'ipca'
                                  AND bi.reference_date <= c.reference_date
                                ORDER BY bi.reference_date DESC
                                LIMIT 1
                            ),
                            (
                                SELECT bi.valor
                                FROM bcb_indicators bi
                                WHERE bi.indicator = 'ipca'
                                ORDER BY bi.reference_date ASC
                                LIMIT 1
                            )
                        ) AS ipca_monthly
                    FROM (SELECT DISTINCT reference_date FROM crypto_with_vol) c
                ),
                selic_annual AS (
                    SELECT
                        reference_date,
                        ROUND(
                            (POWER(1 + selic_daily_rate / 100, 252) - 1) * 100, 6
                        ) as selic_annual_rate
                    FROM bcb_filled
                )
                INSERT INTO daily_consolidated (
                    reference_date, coin_id, price_usd, price_brl, market_cap_usd, 
                    volume_24h_usd, pct_change_1d, volatility_7d,
                    dolar_brl, selic_daily_rate, selic_annual_rate, ipca_monthly, created_at
                )
                SELECT
                    c.reference_date,
                    c.coin_id,
                    c.price_usd,
                    ROUND(c.price_usd * b.dolar_brl, 8) as price_brl,
                    c.market_cap_usd,
                    c.volume_24h_usd,
                    c.pct_change_1d,
                    c.volatility_7d,
                    b.dolar_brl,
                    b.selic_daily_rate,
                    s.selic_annual_rate,
                    b.ipca_monthly,
                    NOW()
                FROM crypto_with_vol c
                LEFT JOIN bcb_filled b ON c.reference_date = b.reference_date
                LEFT JOIN selic_annual s ON b.reference_date = s.reference_date
                ON CONFLICT (coin_id, reference_date) DO UPDATE
                SET 
                    price_usd = EXCLUDED.price_usd,
                    price_brl = EXCLUDED.price_brl,
                    market_cap_usd = EXCLUDED.market_cap_usd,
                    volume_24h_usd = EXCLUDED.volume_24h_usd,
                    pct_change_1d = EXCLUDED.pct_change_1d,
                    volatility_7d = EXCLUDED.volatility_7d,
                    dolar_brl = EXCLUDED.dolar_brl,
                    selic_daily_rate = EXCLUDED.selic_daily_rate,
                    selic_annual_rate = EXCLUDED.selic_annual_rate,
                    ipca_monthly = EXCLUDED.ipca_monthly,
                    created_at = EXCLUDED.created_at
                """)
                
                conn.execute(consolidation_sql, {"start_date": start_date})
            
            logger.info(f"✓ Consolidação concluída")
            
            # Retornar número de registros na tabela
            with self.engine.connect() as conn:
                count = conn.execute(text("SELECT COUNT(*) FROM daily_consolidated")).scalar()
            
            return count
        
        except Exception as e:
            logger.error(f"✗ Erro ao consolidar: {str(e)}")
            raise
    
    def log_pipeline_run(self, dag_id: str, task_id: str, source: str, status: str, 
                        rows_inserted: int = 0, error_message: str = None) -> None:
        """
        Registra execução do pipeline em pipeline_run_log.
        
        Args:
            dag_id: ID da DAG
            task_id: ID da tarefa
            source: Fonte (coingecko ou bcb)
            status: Status (success, failed, skipped)
            rows_inserted: Número de linhas inseridas
            error_message: Mensagem de erro (se houver)
        """
        try:
            with self.engine.begin() as conn:
                query = text("""
                INSERT INTO pipeline_run_log (dag_id, task_id, source, status, rows_inserted, error_message, started_at, finished_at)
                VALUES (:dag_id, :task_id, :source, :status, :rows_inserted, :error_message, NOW(), NOW())
                """)
                
                conn.execute(query, {
                    "dag_id": dag_id,
                    "task_id": task_id,
                    "source": source,
                    "status": status,
                    "rows_inserted": rows_inserted,
                    "error_message": error_message,
                })
            
            logger.info(f"✓ Pipeline run registrado: {dag_id}/{task_id} - {status}")
        
        except Exception as e:
            logger.warning(f"⚠ Erro ao registrar pipeline run: {str(e)}")
