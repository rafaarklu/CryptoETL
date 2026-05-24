"""DAG do Airflow para consolidação de dados em tabela analítica diária.

Esta DAG agrupa as etapas do pipeline em sequência (mínimo 4 tasks) para
atender ao requisito de orquestração com múltiplas tarefas e dependências.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

from src.pipelines.run_pipeline import (
    run_bcb_extraction,
    run_coingecko_extraction,
    run_consolidation,
)
from src.loaders.postgres_loader import PostgresLoader
from src.settings import AIRFLOW_DAG_OWNER, AIRFLOW_DEFAULT_RETRIES, AIRFLOW_CATCHUP

# Argumentos padrão da DAG
default_args = {
    "owner": AIRFLOW_DAG_OWNER,
    "retries": AIRFLOW_DEFAULT_RETRIES,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2026, 5, 8),
}


dag_obj = DAG(
    "dag_consolidate",
    default_args=default_args,
    description=(
        "Pipeline completo: extrai BCB e CoinGecko, consolida e valida resultado"
    ),
    schedule_interval="30 6 * * *",
    catchup=AIRFLOW_CATCHUP,
    max_active_runs=1,
    tags=["etl", "consolidation", "analytics"],
)


def task_extract_bcb(**kwargs):
    return run_bcb_extraction(dag_id=kwargs.get("dag").dag_id, task_id="extract_bcb")


def task_extract_coingecko(**kwargs):
    return run_coingecko_extraction(dag_id=kwargs.get("dag").dag_id, task_id="extract_crypto")


def task_consolidate(**kwargs):
    return run_consolidation(dag_id=kwargs.get("dag").dag_id, task_id="consolidate_daily_tables")


def task_validate(**kwargs):
    """Validação simples pós-consolidação: checa se existem registros na tabela."""
    loader = PostgresLoader()
    count = loader.engine.execute("SELECT COUNT(*) FROM daily_consolidated").scalar()
    if count is None:
        raise ValueError("Validação falhou: não foi possível contar registros em daily_consolidated")
    return int(count)


extract_bcb_op = PythonOperator(
    task_id="extract_bcb",
    python_callable=task_extract_bcb,
    dag=dag_obj,
    provide_context=True,
)

extract_coingecko_op = PythonOperator(
    task_id="extract_coingecko",
    python_callable=task_extract_coingecko,
    dag=dag_obj,
    provide_context=True,
)

consolidate_op = PythonOperator(
    task_id="consolidate_daily_tables",
    python_callable=task_consolidate,
    dag=dag_obj,
    provide_context=True,
)

validate_op = PythonOperator(
    task_id="validate_consolidation",
    python_callable=task_validate,
    dag=dag_obj,
    provide_context=True,
)

# Definir dependências: BCB -> CoinGecko -> Consolidate -> Validate
extract_bcb_op >> extract_coingecko_op >> consolidate_op >> validate_op

