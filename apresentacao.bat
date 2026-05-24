@echo off
setlocal

REM Ir para a pasta do projeto
cd /d "%~dp0"

echo =========================================
echo CryptoETL - Execucao da apresentacao
echo =========================================
echo.

echo [1/6] Subindo a stack principal...
REM Subir o Postgres primeiro e aguardar ficar saudavel
docker compose up -d postgres
:wait_postgres
for /f "delims=" %%H in ('docker inspect -f "{{.State.Health.Status}}" cryptoetl-postgres-1 2^>nul') do set POSTGRES_HEALTH=%%H
if not defined POSTGRES_HEALTH goto wait_postgres
if /i not "%POSTGRES_HEALTH%"=="healthy" (
	set POSTGRES_HEALTH=
	timeout /t 2 /nobreak >nul
	goto wait_postgres
)

REM Inicializar o Airflow antes de subir webserver e scheduler
docker compose up -d airflow-init
docker wait cryptoetl-airflow-init-1 >nul
if errorlevel 1 (
	echo Erro: airflow-init falhou. Verifique os logs antes de continuar.
	docker compose logs --no-color --tail 100 airflow-init
	goto end
)

REM Subir webserver e scheduler depois da inicializacao
docker compose up -d airflow-webserver airflow-scheduler
echo.

echo [2/6] Conferindo containers...
REM Ver containers ativos
docker compose ps
echo.

echo [3/6] Executando DAGs...
REM Rodar as DAGs de forma sincronizada para garantir que a carga termine antes da validacao
docker exec -i cryptoetl-airflow-webserver-1 airflow dags test dag_extract_bcb 2026-05-24
docker exec -i cryptoetl-airflow-webserver-1 airflow dags test dag_extract_coingecko 2026-05-24
docker exec -i cryptoetl-airflow-webserver-1 airflow dags test dag_consolidate 2026-05-24
echo.

echo [4/6] Validando banco...
REM Conferir carga no banco
docker exec -i cryptoetl-postgres-1 psql -U etl_user -d pipeline_db -c "SELECT COUNT(*) FROM bcb_indicators;"
docker exec -i cryptoetl-postgres-1 psql -U etl_user -d pipeline_db -c "SELECT COUNT(*) FROM crypto_market;"
docker exec -i cryptoetl-postgres-1 psql -U etl_user -d pipeline_db -c "SELECT COUNT(*) FROM daily_consolidated;"
echo.

echo [5/6] Rodando testes...
REM Executar testes unitarios
python -m pytest -q
REM Salvar saida dos testes
python -m pytest -q > reports\screenshots\pytest_output.txt 2>&1
echo.

echo [6/6] Gerando PDF...
REM Gerar o PDF final
.\.venv\Scripts\python.exe scripts\generate_relatorio_pdf.py
echo.
echo [7/7] Iniciando dashboard...
REM Iniciar o dashboard Streamlit em background
start cmd /k "streamlit run app/dashboard.py --server.port 8501"
echo.
echo Dashboard iniciado em http://localhost:8501
echo.
echo =========================================
echo Fim da execucao
echo =========================================
goto cleanup

:end
echo.
echo Execucao interrompida por erro.

:cleanup
pause
endlocal
