# Guia de execução da apresentação — CryptoETL

Este guia organiza a apresentação de forma reproduzível no Windows, com os comandos, o terminal recomendado e os links locais de validação.

## Execução recomendada para a banca

Use esta sequência se você quiser executar tudo de ponta a ponta com o menor número de passos.

### 1. Abrir o terminal na raiz do projeto

Terminal: `cmd`

```cmd
cd /d C:\Users\gustavo.telles\Desktop\CryptoETL
```

### 2. Ativar o ambiente virtual

Terminal: `cmd`

```cmd
c:\Users\gustavo.telles\Desktop\CryptoETL\.venv\Scripts\activate.bat
```

### 3. Executar a apresentação validada

Terminal: `cmd`

```cmd
apresentacao.bat
```

Esse script faz, nesta ordem:

1. sobe a stack principal com Docker Compose;
2. aguarda o Postgres ficar saudável;
3. executa o `airflow-init`;
4. sobe o Airflow Webserver e Scheduler;
5. executa as DAGs de extração e consolidação;
6. valida o banco;
7. roda os testes;
8. gera o PDF do relatório;
9. inicia o dashboard Streamlit em uma nova janela.

## Execução manual detalhada

Se você preferir mostrar cada etapa separadamente, siga esta ordem.

### 4. Subir a infraestrutura base

Terminal: `cmd`

```cmd
docker compose up -d postgres airflow-init airflow-webserver airflow-scheduler
```

### 5. Conferir se os containers subiram

Terminal: `cmd`

```cmd
docker compose ps
```

### 6. Verificar as DAGs no Airflow

Terminal: `cmd`

```cmd
docker exec -i cryptoetl-airflow-webserver-1 airflow dags list
```

### 7. Executar as DAGs na ordem correta

Terminal: `cmd`

Use a data da execução que você quer simular. Se for amanhã, por exemplo 25/05, troque o valor para `2026-05-25`.

```cmd
docker exec -i cryptoetl-airflow-webserver-1 airflow dags test dag_extract_bcb 2026-05-30
```

```cmd
docker exec -i cryptoetl-airflow-webserver-1 airflow dags test dag_extract_coingecko <2026-05-30>
```

```cmd
docker exec -i cryptoetl-airflow-webserver-1 airflow dags test dag_consolidate <2026-05-30>
```

### 8. Conferir os runs no Airflow

Terminal: `cmd`

```cmd
docker exec -i cryptoetl-airflow-webserver-1 airflow dags list-runs -d dag_consolidate
```

### 9. Validar o banco PostgreSQL

Terminal: `cmd`

```cmd
docker exec -i cryptoetl-postgres-1 psql -U etl_user -d pipeline_db -c "SELECT COUNT(*) AS total_bcb FROM bcb_indicators;"
```

```cmd
docker exec -i cryptoetl-postgres-1 psql -U etl_user -d pipeline_db -c "SELECT COUNT(*) AS total_crypto FROM crypto_market;"
```

```cmd
docker exec -i cryptoetl-postgres-1 psql -U etl_user -d pipeline_db -c "SELECT COUNT(*) AS total_consolidated FROM daily_consolidated;"
```

```cmd
docker exec -i cryptoetl-postgres-1 psql -U etl_user -d pipeline_db -c "SELECT COUNT(*) AS nulos_dolar_brl FROM daily_consolidated WHERE dolar_brl IS NULL;"
```

```cmd
docker exec -i cryptoetl-postgres-1 psql -U etl_user -d pipeline_db -c "SELECT * FROM pipeline_run_log ORDER BY finished_at DESC LIMIT 20;"
```

### 10. Rodar os testes unitários

Terminal: `cmd`

```cmd
python -m pytest -q
```

Para salvar a evidência:

```cmd
python -m pytest -q > reports\screenshots\pytest_output.txt 2>&1
```

### 11. Abrir o dashboard

⚠️ **Nota:** Se você rodou `apresentacao.bat`, o dashboard já foi iniciado automaticamente em uma nova janela.

Caso contrário, execute manualmente:

Terminal: `cmd`

```cmd
streamlit run app/dashboard.py --server.port 8501
```

Links locais para validação:

- Airflow: http://localhost:8080
- Dashboard Streamlit: http://localhost:8501

### 12. Gerar o PDF do relatório

Terminal: `cmd`

```cmd
.\.venv\Scripts\python.exe scripts\generate_relatorio_pdf.py
```

## Ordem ideal na apresentação oral

Se usar `apresentacao.bat`:

1. Executar o script de apresentação: `apresentacao.bat`
2. Aguardar a conclusão de todas as etapas (subida da stack, DAGs, testes, PDF e dashboard).
3. Abrir o Airflow em http://localhost:8080 para mostrar as DAGs executadas.
4. Abrir o dashboard em http://localhost:8501 (já estará disponível).
5. Mostrar a validação do PostgreSQL com `0` nulos em `dolar_brl`.
6. Mostrar os testes unitários no arquivo `reports/screenshots/pytest_output.txt`.
7. Mostrar o relatório em PDF.

**Alternativa manual** (se preferir controlar cada etapa):

1. Subir os containers manualmente.
2. Abrir o Airflow e executar as DAGs na ordem: `dag_extract_bcb` → `dag_extract_coingecko` → `dag_consolidate`.
3. Validar o banco PostgreSQL.
4. Executar os testes unitários.
5. Gerar o PDF.
6. Iniciar o dashboard manualmente.

## Evidências e arquivos de apoio

- `reports/screenshots/pytest_output.txt` - saída dos testes automatizados.
- `reports/screenshots/db_counts.csv` - contagem final por ativo na tabela consolidada.
- `reports/screenshots/presentation_text.txt` - transcrição textual da apresentação e dos resultados finais.
- `reports/screenshots/airflow_home.png` - tela inicial do Airflow.
- `reports/screenshots/airflow_graph.png` - visão gráfica da DAG de consolidação.
- `reports/screenshots/dashboard_overview.png` - visão geral do dashboard.
- `reports/screenshots/dashboard_correlation.png` - correlação dólar x Bitcoin.
- `reports/screenshots/dashboard_print.png` - print adicional do dashboard.

## Observações

- Se o `airflow-init` ainda estiver finalizando, aguarde ele concluir antes de disparar as DAGs.
- Se o dashboard não abrir na primeira tentativa, verifique `docker compose ps`.
- Para uma apresentação limpa, feche instâncias antigas do Docker antes de iniciar.
- O fluxo validado final terminou com 19 testes aprovados, 1460 linhas consolidadas e 0 nulos em `dolar_brl`.
