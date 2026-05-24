"""
DAG do Airflow para extração de dados do Banco Central do Brasil (BCB).
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

from src.pipelines.run_pipeline import run_bcb_extraction
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
    "dag_extract_bcb",
    default_args=default_args,
    description="Extrai dados de indicadores econômicos do Banco Central do Brasil (Dólar, SELIC, IPCA)",
    schedule_interval="0 6 * * *",  # Diariamente às 6:00 UTC
    catchup=AIRFLOW_CATCHUP,
    max_active_runs=1,
    tags=["etl", "bcb", "macro"],
)


def extract_bcb_task():
    """Task que executa extração BCB."""
    return run_bcb_extraction(
        dag_id="dag_extract_bcb",
        task_id="extract_bcb",
    )


# Definir task
extract_task = PythonOperator(
    task_id="extract_bcb",
    python_callable=extract_bcb_task,
    dag=dag_obj,
    provide_context=True,
)

# Dependências (neste caso, nenhuma)
extract_task
