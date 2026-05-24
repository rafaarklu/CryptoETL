"""
Interface CLI principal do pipeline ETL CryptoETL.
"""
import logging
import argparse
import sys
from datetime import datetime

from src.pipelines.run_pipeline import run_bcb_extraction, run_coingecko_extraction, run_consolidation, run_all
from src.utils.logging_config import configure_logging

logger = logging.getLogger(__name__)


def main():
    """
    Função principal do CLI.
    """
    configure_logging()

    parser = argparse.ArgumentParser(
        description="CryptoETL - Pipeline de Integração de Dados Macroeconômicos × Criptomoedas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python -m src.main all              # Executar pipeline completo
  python -m src.main bcb              # Apenas extração BCB
  python -m src.main crypto           # Apenas extração CoinGecko
  python -m src.main consolidate      # Apenas consolidação
        """
    )
    
    parser.add_argument(
        "mode",
        choices=["all", "bcb", "crypto", "consolidate"],
        help="Modo de execução",
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Nível de logging (padrão: INFO)",
    )
    
    args = parser.parse_args()
    
    # Ajustar nível de logging
    for handler in logging.root.handlers:
        handler.setLevel(args.log_level)
    logging.getLogger().setLevel(args.log_level)
    
    try:
        if args.mode == "bcb":
            logger.info("Executando extração BCB...")
            result = run_bcb_extraction()
            logger.info(f"✓ Concluído: {result} registros carregados")
        
        elif args.mode == "crypto":
            logger.info("Executando extração CoinGecko...")
            result = run_coingecko_extraction()
            logger.info(f"✓ Concluído: {result} registros carregados")
        
        elif args.mode == "consolidate":
            logger.info("Executando consolidação...")
            result = run_consolidation()
            logger.info(f"✓ Concluído: {result} registros consolidados")
        
        elif args.mode == "all":
            logger.info("Executando pipeline completo...")
            results = run_all()
            logger.info("✓ Pipeline executado com sucesso!")
            sys.exit(0)
    
    except Exception as e:
        logger.error(f"✗ Erro durante execução: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
