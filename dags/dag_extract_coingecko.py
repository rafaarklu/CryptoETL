"""
DAG do Airflow para extração de dados da CoinGecko.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

from src.pipelines.run_pipeline import run_coingecko_extraction
from src.settings import AIRFLOW_DAG_OWNER, AIRFLOW_DEFAULT_RETRIES, AIRFLOW_CATCHUP

# Argumentos padrão da DAG
default_args = {
    "owner": AIRFLOW_DAG_OWNER,
    "retries": AIRFLOW_DEFAULT_RETRIES,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2026, 5, 8),
}

# Definição da DAG
dag_obj = DAG(
    "dag_extract_coingecko",
    default_args=default_args,
    description="Extrai dados de mercado de criptomoedas (Bitcoin, Ethereum, Solana, Binance Coin) da CoinGecko",
    schedule_interval="0 6 * * *",  # Diariamente às 6:00 UTC
    catchup=AIRFLOW_CATCHUP,
    max_active_runs=1,
    tags=["etl", "coingecko", "crypto"],
)


def extract_crypto_task():
    """Task que executa extração CoinGecko."""
    return run_coingecko_extraction(
        dag_id="dag_extract_coingecko",
        task_id="extract_crypto",
    )


# Definir task
extract_task = PythonOperator(
    task_id="extract_crypto",
    python_callable=extract_crypto_task,
    dag=dag_obj,
    provide_context=True,
)

# Dependências (neste caso, nenhuma)
extract_task
