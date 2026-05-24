"""
Extrator de dados da CoinGecko.
"""
import logging
from datetime import datetime, timedelta
import requests
import pandas as pd
import time
import random
from requests.exceptions import RequestException, HTTPError
from src.settings import COINGECKO_API_BASE, CRYPTO_COINS, EXTRACTION_DAYS_BACK

logger = logging.getLogger(__name__)


def extract_coingecko_data() -> pd.DataFrame:
    """
    Extrai dados de mercado da CoinGecko para as criptomoedas especificadas.
    Usa o endpoint market_chart para obter histórico de preços e volumes.
    
    Returns:
        pd.DataFrame: DataFrame com as colunas [coin_id, reference_date, price_usd, volume_24h_usd, market_cap_usd]
    """
    logger.info("Iniciando extração de dados da CoinGecko...")
    
    all_data = []
    
    for coin_id in CRYPTO_COINS:
        logger.info(f"  → Extraindo {coin_id}...")
        
        try:
            # Endpoint: market_chart retorna histórico de preços
            url = f"{COINGECKO_API_BASE}/coins/{coin_id}/market_chart"
            params = {
                "vs_currency": "usd",
                "days": EXTRACTION_DAYS_BACK,
                "interval": "daily",
            }

            # Fazer requisição com retry/backoff para lidar com 429 rate limits
            def _get_with_retries(url, params, max_retries=5, backoff_factor=1.0):
                resp = None
                for attempt in range(1, max_retries + 1):
                    try:
                        resp = requests.get(url, params=params, timeout=30)
                        if resp.status_code == 429:
                            # respeitar Retry-After quando presente
                            ra = resp.headers.get("Retry-After")
                            if ra and ra.isdigit():
                                wait = int(ra)
                            else:
                                wait = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 1)
                            logger.warning(f"    ⚠ 429 recebido, aguardando {wait:.1f}s antes da tentativa {attempt}")
                            time.sleep(wait)
                            # loop e tente novamente
                            continue
                        resp.raise_for_status()
                        return resp
                    except HTTPError as e:
                        status = getattr(resp, 'status_code', None)
                        if status == 429 and attempt < max_retries:
                            wait = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 1)
                            logger.warning(f"    ⚠ HTTPError 429 - retrying in {wait:.1f}s (attempt {attempt})")
                            time.sleep(wait)
                            continue
                        raise
                    except RequestException as e:
                        if attempt < max_retries:
                            wait = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 1)
                            logger.warning(f"    ⚠ Erro de conexão ({e}), tentando novamente em {wait:.1f}s (attempt {attempt})")
                            time.sleep(wait)
                            continue
                        raise

            response = _get_with_retries(url, params)
            
            data = response.json()
            
            # CoinGecko retorna: prices, market_caps, total_volumes (cada um é lista de [timestamp_ms, valor])
            prices_df = pd.DataFrame(data.get("prices", []), columns=["timestamp_ms", "price_usd"])
            market_caps_df = pd.DataFrame(data.get("market_caps", []), columns=["timestamp_ms", "market_cap_usd"])
            volumes_df = pd.DataFrame(data.get("total_volumes", []), columns=["timestamp_ms", "volume_24h_usd"])

            if prices_df.empty:
                logger.warning(f"    ⚠ Nenhum dado de preço recebido para {coin_id}")
                continue

            for frame in (prices_df, market_caps_df, volumes_df):
                if not frame.empty:
                    frame["reference_date"] = pd.to_datetime(frame["timestamp_ms"], unit="ms", utc=True).dt.date

            merged = prices_df[["timestamp_ms", "reference_date", "price_usd"]].copy()
            if not market_caps_df.empty:
                merged = merged.merge(
                    market_caps_df[["reference_date", "market_cap_usd"]],
                    on="reference_date",
                    how="left",
                )
            else:
                merged["market_cap_usd"] = None

            if not volumes_df.empty:
                merged = merged.merge(
                    volumes_df[["reference_date", "volume_24h_usd"]],
                    on="reference_date",
                    how="left",
                )
            else:
                merged["volume_24h_usd"] = None

            # Quando há múltiplos pontos no mesmo dia, preserva o último registro do dia.
            merged = (
                merged.sort_values(["reference_date", "timestamp_ms"])
                .drop_duplicates(subset=["reference_date"], keep="last")
                .reset_index(drop=True)
            )

            logger.info(f"    ✓ Recebidos {len(merged)} dias de dados para {coin_id}")

            for _, row in merged.iterrows():
                all_data.append(
                    {
                        "coin_id": coin_id,
                        "reference_date": row["reference_date"],
                        "price_usd": row["price_usd"],
                        "market_cap_usd": row.get("market_cap_usd"),
                        "volume_24h_usd": row.get("volume_24h_usd"),
                    }
                )
        
        except requests.exceptions.RequestException as e:
            logger.error(f"    ✗ Erro ao extrair {coin_id}: {str(e)}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"    ✗ Erro ao processar dados de {coin_id}: {str(e)}")
            raise
    
    df = pd.DataFrame(all_data)
    logger.info(f"✓ Extração CoinGecko concluída: {len(df)} registros no total")
    
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = extract_coingecko_data()
    print(df.head())
    print(f"\nTotal: {len(df)} registros")
