import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from src.extractors.bcb_extractor import extract_bcb_indicators


def _mock_response(json_data, status=200):
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = json_data
    def raise_for_status():
        if mock.status_code >= 400:
            raise Exception(f"HTTP {mock.status_code}")
    mock.raise_for_status = raise_for_status
    return mock


@patch("src.extractors.bcb_extractor.requests.get")
def test_extract_bcb_success(mock_get):
    # Two indicators, each with two records
    data_usd = [{"data": "01/01/2026", "valor": "5,2"}, {"data": "02/01/2026", "valor": "5,3"}]
    data_selic = [{"data": "01/01/2026", "valor": "0,05"}, {"data": "02/01/2026", "valor": "0,052"}]

    # Mock calls for each indicator in BCB_INDICATORS
    mock_get.side_effect = [
        _mock_response(data_usd),
        _mock_response(data_selic),
        _mock_response([]),
    ]

    df = extract_bcb_indicators()

    assert isinstance(df, pd.DataFrame)
    assert set(["indicator", "reference_date", "valor"]).issubset(df.columns)
    assert len(df) >= 2


@patch("src.extractors.bcb_extractor.time.sleep", return_value=None)
@patch("src.extractors.bcb_extractor.requests.get")
def test_extract_bcb_retries_on_transient_502(mock_get, _mock_sleep):
    data_usd = [{"data": "01/01/2026", "valor": "5,2"}]
    data_selic = [{"data": "01/01/2026", "valor": "0,05"}]

    transient = _mock_response([], status=502)
    transient.headers = {}

    mock_get.side_effect = [
        _mock_response(data_usd),
        transient,
        _mock_response(data_selic),
        _mock_response([]),
    ]

    df = extract_bcb_indicators()

    assert isinstance(df, pd.DataFrame)
    assert len(df) >= 2
