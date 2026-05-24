import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from src.extractors.coingecko_extractor import extract_coingecko_data


def _mock_response(json_data, status=200, headers=None):
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = json_data
    mock.headers = headers or {}
    def raise_for_status():
        if mock.status_code >= 400:
            raise Exception(f"HTTP {mock.status_code}")
    mock.raise_for_status = raise_for_status
    return mock


@patch("src.extractors.coingecko_extractor.requests.get")
def test_extract_coingecko_success(mock_get):
    # Prepare fake data for two coins
    prices = [[1714521600000, 60000], [1714608000000, 60500]]
    market_caps = [[1714521600000, 1000000000], [1714608000000, 1010000000]]
    total_volumes = [[1714521600000, 20000000], [1714608000000, 21000000]]

    # First call (bitcoin)
    mock_get.side_effect = [
        _mock_response({"prices": prices, "market_caps": market_caps, "total_volumes": total_volumes}),
        _mock_response({"prices": prices, "market_caps": market_caps, "total_volumes": total_volumes}),
        _mock_response({"prices": prices, "market_caps": market_caps, "total_volumes": total_volumes}),
        _mock_response({"prices": prices, "market_caps": market_caps, "total_volumes": total_volumes}),
    ]

    df = extract_coingecko_data()

    assert isinstance(df, pd.DataFrame)
    assert "coin_id" in df.columns
    assert "price_usd" in df.columns
    assert len(df) > 0


@patch("src.extractors.coingecko_extractor.requests.get")
def test_extract_coingecko_populates_volume_from_total_volumes(mock_get):
    mock_get.side_effect = [
        _mock_response({
            "prices": [[1714521600000, 60000]],
            "market_caps": [[1714521600000, 1000000000]],
            "total_volumes": [[1714521600000, 20000000]],
        }),
        _mock_response({
            "prices": [[1714521600000, 60000]],
            "market_caps": [[1714521600000, 1000000000]],
            "total_volumes": [[1714521600000, 20000000]],
        }),
        _mock_response({
            "prices": [[1714521600000, 60000]],
            "market_caps": [[1714521600000, 1000000000]],
            "total_volumes": [[1714521600000, 20000000]],
        }),
        _mock_response({
            "prices": [[1714521600000, 60000]],
            "market_caps": [[1714521600000, 1000000000]],
            "total_volumes": [[1714521600000, 20000000]],
        }),
    ]

    df = extract_coingecko_data()

    assert df["volume_24h_usd"].notna().all()
