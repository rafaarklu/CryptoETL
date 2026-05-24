# A api do coin gekko é esquisita. As moedas utilizadas são

- Bitcoin 
(https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=365)

- Ethereum (ETH)
(https://api.coingecko.com/api/v3/coins/ethereum/market_chart?vs_currency=usd&days=365)

- Solana (SOL)          
(https://api.coingecko.com/api/v3/coins/solana/market_chart?vs_currency=usd&days=365)

- Binance Coin (BNB)    
(https://api.coingecko.com/api/v3/coins/binancecoin/market_chart?vs_currency=usd&days=365)




# A estrutura é mais ou menos assim:

{
  "prices": [
    [1714521600000, 62345.21],
    [1714608000000, 63120.55]
  ],
  "market_caps": [
    [1714521600000, 1220000000000],
    [1714608000000, 1235000000000]
  ],
  "total_volumes": [
    [1714521600000, 35000000000],
    [1714608000000, 37000000000]
  ]
}



# OU SEJA

[1714521600000, 62345.21]

[timestamp, preco(em dolar)]


1714521600000 é um UNIX timestamp em milissegundos, precisa converter para data.

pd.to_datetime(1714521600000, unit="ms")



# API do BCB

DOLAR
(https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados?formato=json&dataInicial=01/01/2024&dataFinal=09/05/2026)

SELIC
(https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados?formato=json&dataInicial=01/01/2024&dataFinal=09/05/2026)

IPCA
(https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial=01/01/2024&dataFinal=09/05/2026)