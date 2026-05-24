"""
Testes unitários para o módulo de transformações de criptomoedas.
"""
import pytest
import pandas as pd
import datetime

from src.transformers.crypto_transformer import transform_crypto_data


@pytest.fixture
def sample_crypto_data():
    """Fixture com dados de exemplo de criptomoedas."""
    dates = pd.date_range("2026-01-01", periods=10)
    return pd.DataFrame({
        "coin_id": ["bitcoin"] * 10,
        "reference_date": dates,
        "price_usd": [45000, 45500, 45200, 46000, 45900, 46500, 47000, 46800, 47500, 47200],
        "market_cap_usd": [900_000_000_000] * 10,
        "volume_24h_usd": [30_000_000_000] * 10,
    })


def test_transform_crypto_data_pct_change_calculated(sample_crypto_data):
    """Testa se a variação percentual é calculada."""
    result = transform_crypto_data(sample_crypto_data)
    
    assert "pct_change_1d" in result.columns
    assert result["pct_change_1d"].notna().sum() > 0


def test_transform_crypto_data_volatility_calculated(sample_crypto_data):
    """Testa se a volatilidade 7 dias é calculada."""
    result = transform_crypto_data(sample_crypto_data)
    
    assert "volatility_7d" in result.columns
    # Volatilidade deve ser None nos primeiros dias (rolling window de 7)
    assert result["volatility_7d"].notna().sum() > 0


def test_transform_crypto_data_date_format(sample_crypto_data):
    """Testa se as datas estão no formato correto."""
    result = transform_crypto_data(sample_crypto_data)
    
    assert result["reference_date"].dtype == "object"
    assert all(isinstance(d, datetime.date) for d in result["reference_date"])


def test_transform_crypto_data_sorted_by_coin_and_date(sample_crypto_data):
    """Testa se dados estão ordenados por moeda e data."""
    # Embaralhar dados
    shuffled = sample_crypto_data.sample(frac=1).reset_index(drop=True)
    
    result = transform_crypto_data(shuffled)
    
    # Verificar ordenação
    for coin in result["coin_id"].unique():
        coin_data = result[result["coin_id"] == coin]
        dates = coin_data["reference_date"].tolist()
        assert dates == sorted(dates)


def test_transform_crypto_data_multiple_coins():
    """Testa transformação com múltiplas moedas."""
    data = pd.DataFrame({
        "coin_id": ["bitcoin", "bitcoin", "ethereum", "ethereum"],
        "reference_date": pd.date_range("2026-01-01", periods=4),
        "price_usd": [45000, 45500, 2500, 2510],
        "market_cap_usd": [900_000_000_000, 910_000_000_000, 300_000_000_000, 301_200_000_000],
        "volume_24h_usd": [30_000_000_000, 31_000_000_000, 15_000_000_000, 15_200_000_000],
    })
    
    result = transform_crypto_data(data)
    
    assert len(result) == 4
    assert set(result["coin_id"].unique()) == {"bitcoin", "ethereum"}


def test_transform_crypto_data_removes_nulls():
    """Testa se valores nulos críticos são removidos."""
    data = pd.DataFrame({
        "coin_id": ["bitcoin", "bitcoin", None],
        "reference_date": pd.date_range("2026-01-01", periods=3),
        "price_usd": [45000, None, 45500],
        "market_cap_usd": [900_000_000_000, 910_000_000_000, 920_000_000_000],
        "volume_24h_usd": [30_000_000_000, 31_000_000_000, 32_000_000_000],
    })
    
    result = transform_crypto_data(data)
    
    # Deve remover registros com coin_id ou price_usd nulo
    assert result["coin_id"].notna().all()
    assert result["price_usd"].notna().all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
