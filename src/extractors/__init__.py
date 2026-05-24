"""Extratores de dados para o pipeline ETL."""

from src.extractors.bcb_extractor import extract_bcb_indicators
from src.extractors.coingecko_extractor import extract_coingecko_data

__all__ = ["extract_bcb_indicators", "extract_coingecko_data"]
