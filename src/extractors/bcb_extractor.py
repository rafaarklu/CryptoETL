"""
Extrator de dados do Banco Central do Brasil (BCB).
"""
import logging
from datetime import datetime
import random
import time
import requests
import pandas as pd
from requests.exceptions import HTTPError, RequestException
from src.settings import BCB_API_BASE, BCB_INDICATORS, EXTRACTION_START_DATE, EXTRACTION_END_DATE

logger = logging.getLogger(__name__)

def _get_with_retries(url, params, max_retries=5, backoff_factor=1.0):
    resp = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code in {429, 500, 502, 503, 504}:
                ra = resp.headers.get("Retry-After") if hasattr(resp, "headers") else None
                if ra and str(ra).isdigit():
                    wait = int(ra)
                else:
                    wait = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 1)
                logger.warning(
                    f"    ⚠ HTTP {resp.status_code} recebido, aguardando {wait:.1f}s antes da tentativa {attempt}"
                )
                time.sleep(wait)
                continue

            resp.raise_for_status()
            return resp
        except HTTPError as e:
            status = getattr(resp, "status_code", None)
            if status in {429, 500, 502, 503, 504} and attempt < max_retries:
                wait = backoff_factor * (2 ** (attempt - 1)) + random.uniform(0, 1)
                logger.warning(f"    ⚠ HTTPError {status} - retrying in {wait:.1f}s (attempt {attempt})")
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

    if resp is not None:
        resp.raise_for_status()
    raise RuntimeError("Falha ao obter resposta do BCB após tentativas")


def extract_bcb_indicators() -> pd.DataFrame:
    """
    Extrai dados do BCB (Dólar, SELIC, IPCA) para o período especificado.
    
    Returns:
        pd.DataFrame: DataFrame com as colunas [indicator, reference_date, valor]
    """
    logger.info("Iniciando extração de dados do BCB...")
    
    all_data = []
    
    for indicator_name, indicator_code in BCB_INDICATORS.items():
        logger.info(f"  → Extraindo {indicator_name} (código {indicator_code})...")
        
        try:
            # Montar URL da API
            url = f"{BCB_API_BASE}.{indicator_code}/dados"
            params = {
                "formato": "json",
                "dataInicial": EXTRACTION_START_DATE,
                "dataFinal": EXTRACTION_END_DATE,
            }
            
            # Fazer requisição
            response = _get_with_retries(url, params)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"    ✓ Recebidos {len(data)} registros de {indicator_name}")
            
            # Processa dados para o formato esperado
            for record in data:
                all_data.append({
                    "indicator": indicator_name,
                    "reference_date": record["data"],  # Formato DD/MM/YYYY da API
                    "valor": float(record["valor"].replace(",", ".")),
                })
        
        except requests.exceptions.RequestException as e:
            logger.error(f"    ✗ Erro ao extrair {indicator_name}: {str(e)}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"    ✗ Erro ao processar dados de {indicator_name}: {str(e)}")
            raise
    
    df = pd.DataFrame(all_data)
    logger.info(f"✓ Extração BCB concluída: {len(df)} registros no total")
    
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = extract_bcb_indicators()
    print(df.head())
    print(f"\nTotal: {len(df)} registros")
