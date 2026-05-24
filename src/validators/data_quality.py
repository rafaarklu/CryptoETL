"""Validações de qualidade de dados para o pipeline CryptoETL."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from src.settings import VALIDATION_RULES

logger = logging.getLogger(__name__)


@dataclass
class DataQualityError(ValueError):
    """Erro lançado quando uma regra de qualidade é violada."""

    table_name: str
    message: str

    def __str__(self) -> str:
        return f"{self.table_name}: {self.message}"


def _ensure_columns(df: pd.DataFrame, table_name: str, columns: Iterable[str]) -> None:
    missing_columns = [column for column in columns if column not in df.columns]
    if missing_columns:
        raise DataQualityError(table_name, f"colunas ausentes: {', '.join(missing_columns)}")


def _validate_nulls(df: pd.DataFrame, table_name: str, columns: Iterable[str]) -> None:
    for column in columns:
        null_count = df[column].isna().sum()
        if null_count:
            raise DataQualityError(table_name, f"{column} possui {null_count} valores nulos")


def _validate_duplicates(df: pd.DataFrame, table_name: str, subset: Iterable[str]) -> None:
    duplicate_count = df.duplicated(subset=list(subset)).sum()
    if duplicate_count:
        raise DataQualityError(table_name, f"{duplicate_count} linhas duplicadas em {', '.join(subset)}")


def _validate_ranges(df: pd.DataFrame, table_name: str, ranges: dict[str, tuple[float, float]]) -> None:
    for column, (minimum, maximum) in ranges.items():
        series = pd.to_numeric(df[column], errors="coerce")
        invalid_mask = series.lt(minimum) | series.gt(maximum)
        invalid_count = int(invalid_mask.sum())
        if invalid_count:
            raise DataQualityError(
                table_name,
                f"{column} possui {invalid_count} valores fora do intervalo [{minimum}, {maximum}]",
            )


def validate_bcb_data(df: pd.DataFrame) -> pd.DataFrame:
    """Valida dados transformados do BCB."""

    rules = VALIDATION_RULES["bcb_indicators"]
    required_columns = ["indicator", "reference_date", "valor"]
    _ensure_columns(df, "bcb_indicators", required_columns)
    _validate_nulls(df, "bcb_indicators", rules["null_check"])
    _validate_duplicates(df, "bcb_indicators", ["indicator", "reference_date"])

    indicator_ranges = rules.get("indicator_ranges", {})
    if indicator_ranges:
        for indicator, column_ranges in indicator_ranges.items():
            indicator_frame = df[df["indicator"] == indicator]
            if indicator_frame.empty:
                continue
            _validate_ranges(indicator_frame, f"bcb_indicators[{indicator}]", column_ranges)
    elif "range_check" in rules:
        _validate_ranges(df, "bcb_indicators", rules["range_check"])

    logger.info("✓ Validações BCB aprovadas")
    return df


def validate_crypto_data(df: pd.DataFrame) -> pd.DataFrame:
    """Valida dados transformados da CoinGecko."""

    rules = VALIDATION_RULES["crypto_market"]
    required_columns = ["coin_id", "reference_date", "price_usd", "market_cap_usd", "volume_24h_usd"]
    _ensure_columns(df, "crypto_market", required_columns)
    _validate_nulls(df, "crypto_market", rules["null_check"])
    _validate_duplicates(df, "crypto_market", ["coin_id", "reference_date"])
    _validate_ranges(df, "crypto_market", rules["range_check"])

    logger.info("✓ Validações CoinGecko aprovadas")
    return df


def validate_consolidated_data(df: pd.DataFrame) -> pd.DataFrame:
    """Valida a tabela consolidada antes da carga final."""

    rules = VALIDATION_RULES["daily_consolidated"]
    required_columns = ["coin_id", "reference_date", "price_usd", "dolar_brl", "volatility_7d"]
    _ensure_columns(df, "daily_consolidated", required_columns)
    _validate_nulls(df, "daily_consolidated", rules["null_check"])
    _validate_duplicates(df, "daily_consolidated", ["coin_id", "reference_date"])
    _validate_ranges(df, "daily_consolidated", rules["range_check"])

    logger.info("✓ Validações da tabela consolidada aprovadas")
    return df
