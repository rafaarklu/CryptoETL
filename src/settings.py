"""
Configurações centralizadas para o pipeline ETL.
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# ===== DATABASE CONFIG =====
DB_HOST = os.getenv("ETL_DB_HOST", "localhost")
DB_PORT = int(os.getenv("ETL_DB_PORT", 5432))
DB_NAME = os.getenv("ETL_DB_NAME", "pipeline_db")
DB_USER = os.getenv("ETL_DB_USER", "etl_user")
DB_PASSWORD = os.getenv("ETL_DB_PASSWORD", "etl_pass")

# String de conexão PostgreSQL
DB_CONNECTION_STRING = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ===== API CONFIG =====
BCB_API_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"
COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"

# Indicadores BCB e seus códigos
BCB_INDICATORS = {
    "dolar": 1,      # PTAX - Dólar PTAX
    "selic": 11,     # SELIC - Taxa de juros
    "ipca": 433,     # IPCA - Índice de Preços
}

# Criptomoedas monitoradas
CRYPTO_COINS = ["bitcoin", "ethereum", "solana", "binancecoin"]

# ===== DATE CONFIG =====
# Período padrão de extração (últimos 365 dias)
EXTRACTION_DAYS_BACK = 365
EXTRACTION_START_DATE = (datetime.now() - timedelta(days=EXTRACTION_DAYS_BACK)).strftime("%d/%m/%Y")
EXTRACTION_END_DATE = datetime.now().strftime("%d/%m/%Y")

# ===== AIRFLOW CONFIG =====
AIRFLOW_DAG_OWNER = "etl_team"
AIRFLOW_DEFAULT_RETRIES = 1
AIRFLOW_DEFAULT_RETRY_DELAY_MINUTES = 5
AIRFLOW_CATCHUP = False  # Não executar DAGs retroativas

# ===== LOGGING CONFIG =====
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ===== VALIDATION RULES =====
VALIDATION_RULES = {
    "bcb_indicators": {
        "null_check": ["valor"],
        "indicator_ranges": {
            "dolar": {"valor": (0, 20)},
            "selic": {"valor": (0, 100)},
            "ipca": {"valor": (-20, 20)},
        },
    },
    "crypto_market": {
        "null_check": ["price_usd", "volume_24h_usd"],
        "range_check": {
            "price_usd": (0.0001, 1_000_000),
            "volume_24h_usd": (0, 1_000_000_000_000),
        },
    },
    "daily_consolidated": {
        "null_check": ["price_usd", "dolar_brl"],
        "range_check": {
            "price_usd": (0.0001, 1_000_000),
            "dolar_brl": (1, 10),
            "volatility_7d": (0, 100),
        },
    },
}

if __name__ == "__main__":
    print("✓ Settings carregadas com sucesso")
    print(f"  DB: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"  Período: {EXTRACTION_START_DATE} a {EXTRACTION_END_DATE}")
    print(f"  Criptos: {', '.join(CRYPTO_COINS)}")
