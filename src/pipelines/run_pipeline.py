"""
Orquestração principal do pipeline ETL.
"""
import logging
from datetime import datetime
import sys

import pandas as pd

from src.extractors import extract_bcb_indicators, extract_coingecko_data
from src.transformers import transform_bcb_data, transform_crypto_data
from src.loaders import PostgresLoader
from src.validators import validate_bcb_data, validate_consolidated_data, validate_crypto_data
from src.utils.logging_config import configure_logging

logger = logging.getLogger(__name__)


def run_bcb_extraction(dag_id: str = "dag_extract_bcb", task_id: str = "extract_bcb") -> int:
    """
    Executa extração e carregamento de dados do BCB.
    
    Args:
        dag_id: ID da DAG (para logging)
        task_id: ID da tarefa (para logging)
    
    Returns:
        int: Número de registros carregados
    """
    logger.info("=" * 80)
    logger.info(f"INICIANDO: {dag_id}/{task_id}")
    logger.info("=" * 80)
    
    try:
        # Extract
        logger.info("\n[1/3] EXTRACT")
        df_raw = extract_bcb_indicators()
        
        # Transform
        logger.info("\n[2/3] TRANSFORM")
        df_transformed = transform_bcb_data(df_raw)

        # Validate
        logger.info("\n[2.5/3] VALIDATE")
        validate_bcb_data(df_transformed)
        
        # Load
        logger.info("\n[3/3] LOAD")
        loader = PostgresLoader()
        rows_loaded = loader.load_bcb_indicators(df_transformed)
        loader.log_pipeline_run(dag_id, task_id, "bcb", "success", rows_loaded)
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✓ SUCESSO: {dag_id}/{task_id} - {rows_loaded} registros carregados")
        logger.info("=" * 80)
        
        return rows_loaded
    
    except Exception as e:
        logger.error(f"\n✗ ERRO: {dag_id}/{task_id}")
        logger.error(f"  {str(e)}", exc_info=True)
        
        loader = PostgresLoader()
        loader.log_pipeline_run(dag_id, task_id, "bcb", "failed", error_message=str(e))
        
        raise


def run_coingecko_extraction(dag_id: str = "dag_extract_coingecko", task_id: str = "extract_crypto") -> int:
    """
    Executa extração e carregamento de dados da CoinGecko.
    
    Args:
        dag_id: ID da DAG (para logging)
        task_id: ID da tarefa (para logging)
    
    Returns:
        int: Número de registros carregados
    """
    logger.info("=" * 80)
    logger.info(f"INICIANDO: {dag_id}/{task_id}")
    logger.info("=" * 80)
    
    try:
        # Extract
        logger.info("\n[1/3] EXTRACT")
        df_raw = extract_coingecko_data()
        
        # Transform
        logger.info("\n[2/3] TRANSFORM")
        df_transformed = transform_crypto_data(df_raw)

        # Validate
        logger.info("\n[2.5/3] VALIDATE")
        validate_crypto_data(df_transformed)
        
        # Load
        logger.info("\n[3/3] LOAD")
        loader = PostgresLoader()
        rows_loaded = loader.load_crypto_market(df_transformed)
        loader.log_pipeline_run(dag_id, task_id, "coingecko", "success", rows_loaded)
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✓ SUCESSO: {dag_id}/{task_id} - {rows_loaded} registros carregados")
        logger.info("=" * 80)
        
        return rows_loaded
    
    except Exception as e:
        logger.error(f"\n✗ ERRO: {dag_id}/{task_id}")
        logger.error(f"  {str(e)}", exc_info=True)
        
        loader = PostgresLoader()
        loader.log_pipeline_run(dag_id, task_id, "coingecko", "failed", error_message=str(e))
        
        raise


def run_consolidation(dag_id: str = "dag_consolidate", task_id: str = "consolidate_daily_tables") -> int:
    """
    Executa consolidação de dados em daily_consolidated.
    
    Args:
        dag_id: ID da DAG (para logging)
        task_id: ID da tarefa (para logging)
    
    Returns:
        int: Número de registros na tabela consolidada
    """
    logger.info("=" * 80)
    logger.info(f"INICIANDO: {dag_id}/{task_id}")
    logger.info("=" * 80)
    
    try:
        loader = PostgresLoader()
        logger.info("\nConsolidando dados...")
        
        rows_consolidated = loader.consolidate_daily_table()

        with loader.engine.connect() as connection:
            consolidated_frame = pd.read_sql("SELECT * FROM daily_consolidated", connection)

        validate_consolidated_data(consolidated_frame)
        
        loader.log_pipeline_run(dag_id, task_id, "consolidation", "success", rows_consolidated)
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✓ SUCESSO: {dag_id}/{task_id} - {rows_consolidated} registros consolidados")
        logger.info("=" * 80)
        
        return rows_consolidated
    
    except Exception as e:
        logger.error(f"\n✗ ERRO: {dag_id}/{task_id}")
        logger.error(f"  {str(e)}", exc_info=True)
        
        loader = PostgresLoader()
        loader.log_pipeline_run(dag_id, task_id, "consolidation", "failed", error_message=str(e))
        
        raise


def run_all() -> dict:
    """
    Executa todo o pipeline: BCB → CoinGecko → Consolidação.
    
    Returns:
        dict: Resultado de cada etapa
    """
    logger.info("\n\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 78 + "║")
    logger.info("║" + "PIPELINE CRYPTOETL - EXECUÇÃO COMPLETA".center(78) + "║")
    logger.info("║" + f"Início: {datetime.now().isoformat()}".ljust(78) + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    
    results = {}
    
    try:
        # Etapa 1: BCB
        logger.info("\n\n📊 ETAPA 1: EXTRAÇÃO BCB")
        results["bcb"] = run_bcb_extraction()
        
        # Etapa 2: CoinGecko
        logger.info("\n\n💰 ETAPA 2: EXTRAÇÃO COINGECKO")
        results["crypto"] = run_coingecko_extraction()
        
        # Etapa 3: Consolidação
        logger.info("\n\n🔗 ETAPA 3: CONSOLIDAÇÃO")
        results["consolidated"] = run_consolidation()
        
        logger.info("\n\n")
        logger.info("╔" + "=" * 78 + "╗")
        logger.info("║" + " " * 78 + "║")
        logger.info("║" + "✓ PIPELINE EXECUTADO COM SUCESSO".center(78) + "║")
        logger.info("║" + f"Fim: {datetime.now().isoformat()}".ljust(78) + "║")
        logger.info("║" + " " * 78 + "║")
        logger.info(f"║ BCB: {results['bcb']} registros | Crypto: {results['crypto']} registros | Consolidado: {results['consolidated']} registros".ljust(78) + "║")
        logger.info("║" + " " * 78 + "║")
        logger.info("╚" + "=" * 78 + "╝")
        logger.info("\n")
        
        return results
    
    except Exception as e:
        logger.error("\n\n")
        logger.error("╔" + "=" * 78 + "╗")
        logger.error("║" + " " * 78 + "║")
        logger.error("║" + "✗ PIPELINE FALHOU".center(78) + "║")
        logger.error("║" + f"Erro: {str(e)[:76]}".ljust(78) + "║")
        logger.error("║" + " " * 78 + "║")
        logger.error("╚" + "=" * 78 + "╝")
        logger.error("\n")
        
        raise


if __name__ == "__main__":
    configure_logging()
    
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "bcb":
            run_bcb_extraction()
        elif mode == "crypto":
            run_coingecko_extraction()
        elif mode == "consolidate":
            run_consolidation()
        elif mode == "all":
            run_all()
        else:
            print("Usage: python -m src.pipelines.run_pipeline [bcb|crypto|consolidate|all]")
    else:
        run_all()
