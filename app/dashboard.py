from __future__ import annotations

# Carregar tabela comparativa antes dos gráficos que a usam
# O summary_table deve ser carregado após a definição da função load_table


import os
import sys
import time
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from streamlit.runtime.scriptrunner import get_script_run_ctx
import plotly.express as px
import plotly.graph_objects as go

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
    """Cria engine com retry automático"""
    max_retries = 10
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            engine = create_engine(os.getenv("DASHBOARD_DB_CONNECTION_STRING", DB_CONNECTION_STRING))
            # Testar conexão
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise



@st.cache_data(ttl=300)
def load_table(query: str, params: dict | None = None) -> pd.DataFrame:
    with get_engine().connect() as connection:
        return pd.read_sql(text(query), connection, params=params)



def load_scalar(query: str, params: dict | None = None):
    frame = load_table(query, params)
    if frame.empty:
        return None
    return frame.iloc[0, 0]



def format_number(value, percent=False):
    if value is None:
        return "-"
    if isinstance(value, (int, float)):
        if percent:
            return f"{value * 100:,.0f}%".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(value)



st.title("CryptoETL Dashboard")
st.caption("Leitura analítica da tabela daily_consolidated no PostgreSQL.")

# Health check com retry automático
with st.spinner("🔄 Conectando ao banco de dados..."):
    try:
        engine = get_engine()
        with engine.connect() as connection:
            health_check = connection.execute(text("SELECT 1")).scalar()
    except Exception as exc:  # pragma: no cover - feedback visual no app
        st.error(f"❌ Falha ao conectar no banco de dados. Tentando reconectar...")
        st.info("💡 O banco pode estar iniciando. Atualize a página em alguns segundos.")
        time.sleep(3)
        st.rerun()



# Carregar tabela comparativa após definição das funções
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

# Debug: Verificar se há dados
debug_count = load_scalar("SELECT COUNT(*) FROM daily_consolidated")
if debug_count == 0 or debug_count is None:
    st.error("❌ ERRO: A tabela daily_consolidated está vazia!")
    st.info("💡 Verifique se as DAGs foram executadas e se os dados foram inseridos no banco.")
    st.stop()

# KPIs principais
corr_btc_dolar = load_scalar(
    "SELECT corr(price_brl, dolar_brl) FROM daily_consolidated WHERE coin_id = 'bitcoin'"
)

metric_columns = st.columns(6)

total_rows = load_scalar("SELECT COUNT(*) FROM daily_consolidated")
total_coins = load_scalar("SELECT COUNT(DISTINCT coin_id) FROM daily_consolidated")
latest_date = load_scalar("SELECT MAX(reference_date) FROM daily_consolidated")
avg_btc_price = load_scalar(
    "SELECT AVG(price_brl) FROM daily_consolidated WHERE coin_id = 'bitcoin'"
)
latest_btc_price = load_scalar(
    "SELECT price_brl FROM daily_consolidated WHERE coin_id = 'bitcoin' ORDER BY reference_date DESC LIMIT 1"
)

metric_columns[0].metric("Linhas consolidadas", format_number(total_rows))
metric_columns[1].metric("Ativos", format_number(total_coins))
metric_columns[2].metric("Última data", str(latest_date) if latest_date else "-")
metric_columns[3].metric("Preço médio BTC em BRL", f"R$ {format_number(avg_btc_price)}")
metric_columns[4].metric("Último preço BTC em BRL", f"R$ {format_number(latest_btc_price)}")
metric_columns[5].metric("Correlação dólar x BTC (BRL)", format_number(corr_btc_dolar, percent=True))

st.markdown("### Observação sobre o indicador de preço do Bitcoin")
st.info(
    "O KPI de preço médio do Bitcoin exibe a média histórica de `price_brl` em `daily_consolidated`, "
    "enquanto o KPI de último preço mostra o valor mais recente registrado na base."
)

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






# Gráficos lado a lado
col1, col2 = st.columns(2)

with col1:
    st.subheader("Comparativo de preço médio por ativo (BRL)")
    if not summary_table.empty:
        bar_data = summary_table[["coin_id", "avg_price_brl"]].copy()
        bar_data = bar_data.dropna(subset=["avg_price_brl"])
        if not bar_data.empty:
            bar_data = bar_data.sort_values("avg_price_brl", ascending=False)
            bar_data["avg_price_brl"] = bar_data["avg_price_brl"].astype(float)
            
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                x=bar_data["coin_id"],
                y=bar_data["avg_price_brl"],
                marker_color="#00c0f2",
                text=[f"R$ {x:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") for x in bar_data["avg_price_brl"]],
                textposition="outside",
            ))
            
            fig_bar.update_layout(
                title="",
                xaxis_title="Ativo",
                yaxis_title="Preço médio (BRL)",
                plot_bgcolor="#222",
                paper_bgcolor="#222",
                font=dict(color="#fff", size=12),
                height=400,
                margin=dict(l=60, r=40, t=40, b=60),
                hovermode="x",
                showlegend=False,
            )
            st.plotly_chart(fig_bar, use_container_width=True, config={"responsive": True})
        else:
            st.warning("Sem dados de preço médio disponível para exibir.")
    else:
        st.warning("Nenhum dado consolidado disponível.")

with col2:
    st.subheader("Evolução do dólar (dólar/BRL)")
    dolar_history = load_table(
        """
        SELECT reference_date, dolar_brl
        FROM daily_consolidated
        ORDER BY reference_date
        """
    )
    if not dolar_history.empty:
        dolar_history = dolar_history.dropna(subset=["dolar_brl"])
        if not dolar_history.empty:
            fig_dolar = go.Figure()
            fig_dolar.add_trace(go.Scatter(
                x=dolar_history["reference_date"],
                y=dolar_history["dolar_brl"],
                mode="lines",
                line=dict(color="#00c0f2", width=2),
                hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Dólar/BRL: %{y:.4f}<extra></extra>",
            ))
            
            fig_dolar.update_layout(
                title="",
                xaxis_title="Data",
                yaxis_title="Dólar/BRL",
                plot_bgcolor="#222",
                paper_bgcolor="#222",
                font=dict(color="#fff", size=12),
                height=400,
                margin=dict(l=60, r=40, t=40, b=60),
                hovermode="x unified",
                showlegend=False,
            )
            st.plotly_chart(fig_dolar, use_container_width=True, config={"responsive": True})
        else:
            st.warning("Sem dados de evolução do dólar disponível.")
    else:
        st.warning("Nenhum dado de dólar disponível.")



# Função utilitária para formatar a tabela comparativa
def format_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df_fmt = df.copy()
    # Formatar retornos e volatilidade como % sem casas decimais
    df_fmt["avg_daily_return"] = df_fmt["avg_daily_return"].apply(lambda x: f"{int(round(x*100))}%" if pd.notnull(x) else "-")
    df_fmt["avg_volatility"] = df_fmt["avg_volatility"].apply(lambda x: f"{int(round(x*100))}%" if pd.notnull(x) else "-")
    # Formatar preço médio em BRL sem casas decimais
    df_fmt["avg_price_brl"] = df_fmt["avg_price_brl"].apply(lambda x: f"R$ {x:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notnull(x) else "-")
    return df_fmt



# Espaçamento antes da tabela comparativa
st.markdown("""
<div style='margin-top: 2rem;'></div>
""", unsafe_allow_html=True)

# Tabela comparativa ao final do dashboard
st.subheader("Resumo comparativo por ativo")
st.markdown("""
Esta tabela compara os principais indicadores de cada ativo consolidado:

- **Retorno médio diário**: média percentual de variação diária do preço.
- **Volatilidade média**: média percentual da volatilidade de 7 dias.
- **Preço médio em BRL**: valor médio do ativo em reais no período consolidado.

Valores negativos indicam queda média no período. Volatilidade maior indica maior oscilação de preço.
""")

if not summary_table.empty:
    st.dataframe(format_summary_table(summary_table), use_container_width=True, hide_index=True)
else:
    st.warning("Nenhum dado de resumo comparativo disponível para exibir.")



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
