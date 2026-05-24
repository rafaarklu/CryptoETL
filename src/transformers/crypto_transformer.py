"""
Transformações para dados de criptomoedas (CoinGecko).
"""
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def transform_crypto_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma dados brutos da CoinGecko para o formato esperado no banco.
    
    Transformações:
    - Garante que reference_date é do tipo date
    - Calcula pct_change_1d (variação % vs dia anterior)
    - Calcula volatility_7d (desvio padrão rolling 7 dias)
    - Remove registros nulos
    - Ordena por moeda e data
    
    Args:
        df: DataFrame com as colunas [coin_id, reference_date, price_usd, market_cap_usd, volume_24h_usd]
    
    Returns:
        pd.DataFrame: DataFrame transformado com colunas adicionais pct_change_1d e volatility_7d
    """
    logger.info("Iniciando transformação de dados de criptomoedas...")
    
    df = df.copy()
    
    # Garantir que reference_date é do tipo date (sempre convertemos)
    df["reference_date"] = pd.to_datetime(df["reference_date"]).dt.date
    
    # Ordenar por moeda e data
    df = df.sort_values(["coin_id", "reference_date"]).reset_index(drop=True)
    
    # Remover registros nulos em colunas críticas
    null_critical = df[["coin_id", "reference_date", "price_usd"]].isnull().sum()
    if null_critical.any():
        logger.warning(f"  ⚠ Encontrados valores nulos: {null_critical.to_dict()}")
        df = df.dropna(subset=["coin_id", "reference_date", "price_usd"])
    
    # Calcular variação diária (pct_change_1d) por moeda
    df["pct_change_1d"] = df.groupby("coin_id")["price_usd"].pct_change() * 100
    
    # Calcular volatilidade 7 dias (desvio padrão rolling da variação)
    df["volatility_7d"] = (
        df.groupby("coin_id")["pct_change_1d"]
        .transform(lambda x: x.rolling(window=7, min_periods=1).std())
    )
    
    logger.info(f"  ✓ pct_change_1d calculado para {(~df['pct_change_1d'].isnull()).sum()} registros")
    logger.info(f"  ✓ volatility_7d calculado para {(~df['volatility_7d'].isnull()).sum()} registros")
    
    logger.info(f"✓ Transformação de cripto concluída: {len(df)} registros")
    
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Teste com dados de exemplo
    test_data = pd.DataFrame({
        "coin_id": ["bitcoin", "bitcoin", "bitcoin", "ethereum", "ethereum"],
        "reference_date": pd.date_range("2026-01-01", periods=5),
        "price_usd": [45000, 45500, 45200, 2500, 2510],
        "market_cap_usd": [900_000_000_000, 910_000_000_000, 904_000_000_000, 300_000_000_000, 301_200_000_000],
        "volume_24h_usd": [30_000_000_000, 31_000_000_000, 29_500_000_000, 15_000_000_000, 15_200_000_000],
    })
    
    result = transform_crypto_data(test_data)
    print(result)
