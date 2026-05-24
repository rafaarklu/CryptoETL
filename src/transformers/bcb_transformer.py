"""
Transformações para dados do BCB.
"""
import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


def transform_bcb_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma dados brutos do BCB para o formato esperado no banco.
    
    Transformações:
    - Converte datas de DD/MM/YYYY para DATE
    - Calcula SELIC anualizada
    - Remove registros nulos
    
    Args:
        df: DataFrame com as colunas [indicator, reference_date, valor]
    
    Returns:
        pd.DataFrame: DataFrame transformado
    """
    logger.info("Iniciando transformação de dados BCB...")
    
    df = df.copy()
    
    # Converter data de DD/MM/YYYY para DATE
    df["reference_date"] = pd.to_datetime(df["reference_date"], format="%d/%m/%Y").dt.date
    
    # SELIC: calcular taxa anualizada
    # Fórmula: ((1 + selic_diaria/100)^252 - 1) * 100
    selic_mask = df["indicator"] == "selic"
    if selic_mask.any():
        df.loc[selic_mask, "selic_annual"] = (
            ((1 + df.loc[selic_mask, "valor"] / 100) ** 252 - 1) * 100
        )
        logger.info(f"  ✓ SELIC anualizada calculada para {selic_mask.sum()} registros")
    
    # Remover registros nulos
    null_count = df["valor"].isnull().sum()
    if null_count > 0:
        logger.warning(f"  ⚠ Removendo {null_count} registros nulos")
        df = df.dropna(subset=["valor"])
    
    logger.info(f"✓ Transformação BCB concluída: {len(df)} registros")
    
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Teste com dados de exemplo
    test_data = pd.DataFrame({
        "indicator": ["dolar", "selic", "ipca", "dolar"],
        "reference_date": ["01/01/2026", "02/01/2026", "03/01/2026", "04/01/2026"],
        "valor": [5.2, 0.05, 0.45, 5.18],
    })
    
    result = transform_bcb_data(test_data)
    print(result)
