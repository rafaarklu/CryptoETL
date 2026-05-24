"""Dashboard Streamlit para exploração da base consolidada do CryptoETL."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from streamlit.runtime.scriptrunner import get_script_run_ctx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.settings import DB_CONNECTION_STRING


st.set_page_config(
    page_title="CryptoETL Dashboard",
    page_icon="📈",
    layout="wide",
)


@st.cache_resource
def get_engine():
    return create_engine(os.getenv("DASHBOARD_DB_CONNECTION_STRING", DB_CONNECTION_STRING))


@st.cache_data(ttl=300)
def load_table(query: str, params: dict | None = None) -> pd.DataFrame:
    with get_engine().connect() as connection:
        return pd.read_sql(text(query), connection, params=params)


def load_scalar(query: str, params: dict | None = None):
    frame = load_table(query, params)
    if frame.empty:
        return None
    return frame.iloc[0, 0]


def format_number(value):
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(value)


st.title("CryptoETL Dashboard")
st.caption("Leitura analítica da tabela daily_consolidated no PostgreSQL.")

try:
    engine = get_engine()
    with engine.connect() as connection:
        health_check = connection.execute(text("SELECT 1")).scalar()
except Exception as exc:  # pragma: no cover - feedback visual no app
    st.error(f"Falha ao conectar no banco de dados: {exc}")
    st.stop()


metric_columns = st.columns(4)

total_rows = load_scalar("SELECT COUNT(*) FROM daily_consolidated")
total_coins = load_scalar("SELECT COUNT(DISTINCT coin_id) FROM daily_consolidated")
latest_date = load_scalar("SELECT MAX(reference_date) FROM daily_consolidated")
avg_btc_price = load_scalar(
    "SELECT AVG(price_brl) FROM daily_consolidated WHERE coin_id = 'bitcoin'"
)

metric_columns[0].metric("Linhas consolidadas", format_number(total_rows))
metric_columns[1].metric("Ativos", format_number(total_coins))
metric_columns[2].metric("Última data", str(latest_date) if latest_date else "-")
metric_columns[3].metric("Preço médio BTC em BRL", format_number(avg_btc_price))

coin_list = load_table(
    "SELECT DISTINCT coin_id FROM daily_consolidated ORDER BY coin_id"
)["coin_id"].tolist()

if not coin_list:
    st.warning("Ainda não há dados em daily_consolidated para exibir.")
    st.stop()

selected_coin = st.selectbox("Selecione o ativo", coin_list, index=0)

coin_history = load_table(
    """
    SELECT reference_date, price_usd, price_brl, pct_change_1d, volatility_7d, dolar_brl, selic_annual_rate, ipca_monthly
    FROM daily_consolidated
    WHERE coin_id = :coin_id
    ORDER BY reference_date
    """,
    {"coin_id": selected_coin},
)

left, right = st.columns(2)

with left:
    st.subheader(f"Preço em BRL - {selected_coin}")
    price_chart = coin_history[["reference_date", "price_brl"]].dropna(subset=["price_brl"])
    st.line_chart(price_chart.set_index("reference_date")["price_brl"])

with right:
    st.subheader(f"Volatilidade 7 dias - {selected_coin}")
    volatility_chart = coin_history[["reference_date", "volatility_7d"]].dropna(subset=["volatility_7d"])
    st.line_chart(volatility_chart.set_index("reference_date")["volatility_7d"])

summary_table = load_table(
    """
    SELECT
        coin_id,
        ROUND(AVG(pct_change_1d)::numeric, 4) AS avg_daily_return,
        ROUND(AVG(volatility_7d)::numeric, 4) AS avg_volatility,
        ROUND(AVG(price_brl)::numeric, 4) AS avg_price_brl
    FROM daily_consolidated
    GROUP BY coin_id
    ORDER BY avg_volatility DESC
    """
)

st.subheader("Resumo comparativo por ativo")
st.dataframe(summary_table, use_container_width=True, hide_index=True)

correlation_table = load_table(
    """
    SELECT
        corr(price_brl, dolar_brl) AS corr_btc_dolar
    FROM daily_consolidated
    WHERE coin_id = 'bitcoin'
    """
)

st.subheader("Correlação dólar x Bitcoin em BRL")
st.metric(
    "corr(price_brl, dolar_brl)",
    format_number(correlation_table.iloc[0, 0]) if not correlation_table.empty else "-",
)


if __name__ == "__main__" and get_script_run_ctx() is None:
    from streamlit.web import cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        __file__,
        "--server.address",
        "0.0.0.0",
        "--server.port",
        "8501",
    ]
    raise SystemExit(stcli.main())
