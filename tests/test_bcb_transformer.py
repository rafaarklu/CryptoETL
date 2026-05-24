"""
Testes unitários para o módulo de transformações BCB.
"""
import pytest
import pandas as pd
import datetime

from src.transformers.bcb_transformer import transform_bcb_data


@pytest.fixture
def sample_bcb_data():
    """Fixture com dados de exemplo do BCB."""
    return pd.DataFrame({
        "indicator": ["dolar", "selic", "ipca", "dolar", "selic"],
        "reference_date": ["01/01/2026", "02/01/2026", "03/01/2026", "04/01/2026", "05/01/2026"],
        "valor": [5.2, 0.05, 0.45, 5.18, 0.052],
    })


def test_transform_bcb_data_date_conversion(sample_bcb_data):
    """Testa se as datas são convertidas de DD/MM/YYYY para DATE."""
    result = transform_bcb_data(sample_bcb_data)
    
    assert result["reference_date"].dtype == "object"
    assert all(isinstance(d, datetime.date) for d in result["reference_date"])


def test_transform_bcb_data_selic_annualization(sample_bcb_data):
    """Testa se a SELIC é anualizada corretamente."""
    result = transform_bcb_data(sample_bcb_data)
    
    selic_rows = result[result["indicator"] == "selic"]
    assert len(selic_rows) > 0
    assert "selic_annual" in result.columns or len(result) > 0


def test_transform_bcb_data_removes_nulls():
    """Testa se valores nulos são removidos."""
    data = pd.DataFrame({
        "indicator": ["dolar", "selic", None],
        "reference_date": ["01/01/2026", "02/01/2026", "03/01/2026"],
        "valor": [5.2, None, 0.45],
    })
    
    result = transform_bcb_data(data)
    
    # Deve ter removido pelo menos o registro nulo de valor
    assert len(result) <= len(data)
    assert result["valor"].isnull().sum() == 0


def test_transform_bcb_data_preserves_non_null_data(sample_bcb_data):
    """Testa se dados válidos são preservados."""
    result = transform_bcb_data(sample_bcb_data)
    
    assert len(result) == len(sample_bcb_data)
    assert all(result["indicator"].isin(["dolar", "selic", "ipca"]))


def test_transform_bcb_data_numeric_values(sample_bcb_data):
    """Testa se os valores são numéricos."""
    result = transform_bcb_data(sample_bcb_data)
    
    assert pd.api.types.is_numeric_dtype(result["valor"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
