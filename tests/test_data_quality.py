"""Testes para validações de qualidade de dados."""

import pandas as pd
import pytest

from src.validators import (
    DataQualityError,
    validate_bcb_data,
    validate_consolidated_data,
    validate_crypto_data,
)


def test_validate_bcb_data_accepts_valid_frame():
    frame = pd.DataFrame(
        {
            "indicator": ["dolar", "selic"],
            "reference_date": [pd.Timestamp("2026-01-01").date(), pd.Timestamp("2026-01-02").date()],
            "valor": [5.2, 0.05],
        }
    )

    result = validate_bcb_data(frame)

    assert result.equals(frame)


def test_validate_bcb_data_accepts_negative_ipca():
    frame = pd.DataFrame(
        {
            "indicator": ["ipca"],
            "reference_date": [pd.Timestamp("2026-01-01").date()],
            "valor": [-0.12],
        }
    )

    result = validate_bcb_data(frame)

    assert result.equals(frame)


def test_validate_crypto_data_rejects_duplicates():
    frame = pd.DataFrame(
        {
            "coin_id": ["bitcoin", "bitcoin"],
            "reference_date": [pd.Timestamp("2026-01-01").date(), pd.Timestamp("2026-01-01").date()],
            "price_usd": [45000, 46000],
            "market_cap_usd": [900_000_000_000, 910_000_000_000],
            "volume_24h_usd": [30_000_000_000, 31_000_000_000],
        }
    )

    with pytest.raises(DataQualityError, match="linhas duplicadas"):
        validate_crypto_data(frame)


def test_validate_consolidated_data_rejects_out_of_range_values():
    frame = pd.DataFrame(
        {
            "coin_id": ["bitcoin"],
            "reference_date": [pd.Timestamp("2026-01-01").date()],
            "price_usd": [45000],
            "dolar_brl": [50],
            "volatility_7d": [5],
        }
    )

    with pytest.raises(DataQualityError, match="dolar_brl"):
        validate_consolidated_data(frame)
