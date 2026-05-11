# Pipeline de Integração: Indicadores Macroeconômicos Brasileiros × Mercado de Criptomoedas

Pipeline de dados end-to-end que cruza indicadores econômicos do Banco Central do Brasil com dados do mercado de criptomoedas, permitindo análises de correlação entre variáveis macro e ativos digitais.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Stack Tecnológica](#stack-tecnológica)
- [Fontes de Dados](#fontes-de-dados)
- [Arquitetura do Pipeline](#arquitetura-do-pipeline)
- [Estrutura do Banco de Dados](#estrutura-do-banco-de-dados)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Como Executar](#como-executar)
- [Análises Previstas](#análises-previstas)

---

## Visão Geral

O projeto implementa um pipeline ETL orquestrado com Apache Airflow que extrai dados de duas APIs públicas, realiza transformações e consolida tudo em uma tabela analítica diária. O objetivo principal é identificar possíveis relações entre variáveis econômicas brasileiras e o comportamento do mercado cripto.

**Exemplos de análises habilitadas pelo pipeline:**

- Impacto da variação do dólar sobre o preço do Bitcoin em reais
- Influência da taxa SELIC sobre ativos de risco como ETH e SOL
- Correlação entre IPCA e volatilidade do mercado cripto
- Comparação de tendências entre os 4 ativos ao longo do tempo

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Orquestração | Apache Airflow 2.x |
| Banco de dados | PostgreSQL 15 |
| Containerização | Docker + Docker Compose |
| Bibliotecas principais | `requests`, `pandas`, `psycopg2`, `sqlalchemy` |

---

## Fontes de Dados

### Banco Central do Brasil (SGS)

Base: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados`

| Indicador | Código SGS | Granularidade | Exemplo de valor |
|---|---|---|---|
| Cotação do Dólar (PTAX) | 1 | Diária (dias úteis) | `4.8916` |
| Taxa SELIC | 11 | Diária (dias úteis) | `0.043739` (% ao dia) |
| IPCA | 433 | Mensal | `0.42` (% no mês) |

Formato de resposta:
```json
[
  {"data": "02/01/2024", "valor": "4.8916"},
  {"data": "03/01/2024", "valor": "4.9212"}
]
```

### CoinGecko

Base: `https://api.coingecko.com/api/v3/coins/{id}/market_chart`

| Ativo | ID na API | Símbolo |
|---|---|---|
| Bitcoin | `bitcoin` | BTC |
| Ethereum | `ethereum` | ETH |
| Solana | `solana` | SOL |
| Binance Coin | `binancecoin` | BNB |

Parâmetros: `vs_currency=usd&days=365`

Formato de resposta:
```json
{
  "prices":       [[1711843200000, 69702.30], [1711929600000, 71246.95]],
  "market_caps":  [[1711843200000, 1370247487960.09], [...]],
  "total_volumes": [[1711843200000, 16408802301.83], [...]]
}
```

> Cada array retorna pares `[timestamp_unix_ms, valor]`. Para 365 dias, a granularidade é horária (~8760 pontos por ativo).

---

## Arquitetura do Pipeline

```
┌─────────────────────┐        ┌──────────────────────┐
│   API Banco Central │        │    API CoinGecko      │
│  Dólar / SELIC /    │        │  BTC / ETH / SOL /    │
│  IPCA               │        │  BNB                  │
└────────┬────────────┘        └──────────┬────────────┘
         │  Extract                        │  Extract
         ▼                                 ▼
┌─────────────────────┐        ┌──────────────────────┐
│   bcb_indicators    │        │    crypto_market      │
│   (dados brutos)    │        │    (dados brutos)     │
└────────┬────────────┘        └──────────┬────────────┘
         │                                 │
         └──────────────┬──────────────────┘
                        │  Transform & Load
                        ▼
             ┌─────────────────────┐
             │  daily_consolidated │
             │  (tabela analítica) │
             └─────────────────────┘
```

### Etapas do ETL

**Extract** — chamadas às APIs do BCB e CoinGecko com os parâmetros de data configurados. Os dados são inseridos nas tabelas brutas com constraint `UNIQUE` para garantir idempotência (reexecuções não duplicam registros).

**Transform** — processamento aplicado antes da consolidação:

- Dólar e SELIC: conversão de `DD/MM/YYYY` para `DATE` do PostgreSQL
- SELIC: cálculo da taxa anualizada → `((1 + taxa_diaria/100)^252 - 1) * 100`
- IPCA: forward fill do valor mensal para cada dia do mês correspondente
- CoinGecko: conversão de timestamp Unix (ms) para data, agregação horária → diária (preço de fechamento, volume somado)
- `price_brl`: `price_usd × dolar_brl` do mesmo dia

**Load** — gravação na tabela `daily_consolidated` com os dados de ambas as fontes alinhados por `reference_date`.

---

## Estrutura do Banco de Dados

O banco utiliza 3 tabelas no schema `public` do PostgreSQL.

### `bcb_indicators`
Armazena os dados brutos das três séries do BCB. A coluna `indicator` diferencia os registros.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador |
| `reference_date` | DATE | Data de referência |
| `indicator` | VARCHAR | `dolar` \| `selic` \| `ipca` |
| `valor` | NUMERIC | Valor conforme retornado pela API |
| `ingested_at` | TIMESTAMP | Data/hora da ingestão |

### `crypto_market`
Armazena os dados brutos do CoinGecko, agregados para granularidade diária.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador |
| `coin_id` | VARCHAR | `bitcoin` \| `ethereum` \| `solana` \| `binancecoin` |
| `reference_date` | DATE | Data de referência |
| `price_usd` | NUMERIC | Preço de fechamento em USD |
| `market_cap_usd` | NUMERIC | Capitalização de mercado em USD |
| `volume_24h_usd` | NUMERIC | Volume negociado em 24h em USD |
| `ingested_at` | TIMESTAMP | Data/hora da ingestão |

### `daily_consolidated`
Tabela principal para análises. Resultado do join e transformação das duas tabelas acima.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL PK | Identificador |
| `reference_date` | DATE | Data de referência |
| `coin_id` | VARCHAR | Ativo criptomoeda |
| `price_usd` | NUMERIC | Preço em USD |
| `price_brl` | NUMERIC | Preço em BRL (`price_usd × dolar_brl`) |
| `market_cap_usd` | NUMERIC | Market cap em USD |
| `volume_24h_usd` | NUMERIC | Volume 24h em USD |
| `pct_change_1d` | NUMERIC | Variação % vs dia anterior |
| `volatility_7d` | NUMERIC | Desvio padrão rolling 7 dias |
| `dolar_brl` | NUMERIC | Cotação do dólar do dia |
| `selic_daily_rate` | NUMERIC | Taxa SELIC diária (%) |
| `selic_annual_rate` | NUMERIC | Taxa SELIC anualizada (%) |
| `ipca_monthly` | NUMERIC | IPCA do mês (forward fill) |
| `created_at` | TIMESTAMP | Data/hora da consolidação |

---

## Estrutura do Projeto

```
CryptoETL/
├── dags/
│   ├── dag_extract_bcb.py
│   ├── dag_extract_coingecko.py
│   └── dag_consolidate.py
├── src/
│   ├── extractors/
│   ├── transformers/
│   ├── loaders/
│   ├── pipelines/
│   ├── settings.py
│   └── main.py
├── db/
│   └── init.sql
├── docker-compose.yml
├── dockerfile
├── requirements.txt
└── .env.example
```

---

## Como Executar

### Pré-requisitos

- Docker e Docker Compose instalados
- Python 3.11+

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/pipeline-macro-cripto.git
cd pipeline-macro-cripto
```

### 2. Configurar variáveis de ambiente

Copie `.env.example` para `.env` e ajuste se precisar.

### 3. Subir os containers

```bash
docker compose up -d postgres airflow-init airflow-webserver airflow-scheduler
```

### 4. Acessar o Airflow

Abra `http://localhost:8080` no navegador.
Credenciais padrão: `airflow / airflow`

### 5. Ativar as DAGs

Na interface do Airflow, ative as DAGs nesta ordem:

1. `dag_extract_bcb`
2. `dag_extract_coingecko`
3. `dag_consolidate`

### 6. Rodar a pipeline localmente sem Airflow

```bash
python -m src.main all
```

Ou, pelo container:

```bash
docker compose --profile tools run --rm etl-cli
```

---

## Análises Previstas

Com a tabela `daily_consolidated` populada, as principais análises planejadas são:

- **Correlação Dólar × Bitcoin (BRL)** — verificar se a alta do dólar impacta o preço do BTC em reais
- **SELIC × Volatilidade cripto** — períodos de juros altos tendem a reduzir exposição a ativos de risco?
- **IPCA × Mercado cripto** — criptomoedas funcionam como hedge contra inflação no Brasil?
- **Comparativo entre ativos** — qual dos 4 ativos apresentou maior correlação com os indicadores macro no período?

## Observações Técnicas

- As cargas usam `UPSERT` com chave única para manter idempotência.
- O schema do banco é criado automaticamente pelo arquivo `db/init.sql` na inicialização do Postgres.
- O Airflow roda com `LocalExecutor` para simplificar a execução local do trabalho.
