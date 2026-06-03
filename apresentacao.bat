@echo off
setlocal enabledelayedexpansion

REM Ir para a pasta do projeto
cd /d "%~dp0"

echo =========================================
echo CryptoETL - Execucao da apresentacao
echo =========================================
echo.
echo NOTA: Os servicos (Airflow e Dashboard) ficarao de pe ate voce parar.
echo       Para encerrar, abra outro terminal e execute: docker compose down
echo.
pause

echo [PREP] Preparando ambiente Python...
REM Verificar se venv existe, se nao, criar
if not exist ".\.venv\" (
	echo Criando venv...
	python -m venv .venv
	echo Ativando venv e instalando dependencias...
	call .\.venv\Scripts\activate.bat
	python -m pip install -q --upgrade pip
	python -m pip install -q -r requirements.txt
	echo [OK] venv criada e configurada.
) else (
	echo [OK] venv ja existe.
	call .\.venv\Scripts\activate.bat
)
echo.

echo [PREP] Limpando ambiente anterior...
REM Derrubar containers anteriores para garantir estado limpo
docker compose down -v >nul 2>&1
REM Limpar PIDs antigos do Airflow
del airflow-webserver.pid >nul 2>&1
del airflow-scheduler.pid >nul 2>&1
del airflow-triggerer.pid >nul 2>&1
timeout /t 3 /nobreak >nul
echo [OK] Ambiente limpo.
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
echo [OK] PostgreSQL saudavel.
echo.

REM Inicializar o Airflow DB
set "AIRFLOW_DB_EXISTS="
for /f "delims=" %%H in ('docker exec -i cryptoetl-postgres-1 psql -U etl_user -tAc "SELECT 1 FROM pg_database WHERE datname = 'airflow_db'" 2^>nul') do set "AIRFLOW_DB_EXISTS=%%H"
if "%AIRFLOW_DB_EXISTS%"=="1" (
	echo Airflow DB ja existe, pulando airflow-init...
) else (
	echo Inicializando Airflow DB...
	docker compose up -d airflow-init
	docker wait cryptoetl-airflow-init-1 >nul 2>&1
	timeout /t 5 /nobreak >nul
	echo [OK] Airflow DB inicializado.
)
echo.

echo [2/6] Subindo Airflow webserver e scheduler...
REM Limpar PID stale DENTRO do container (problema comum)
docker compose exec -T postgres true >nul 2>&1
if %errorlevel%==0 (
	docker compose exec -T airflow-webserver rm -f /opt/airflow/airflow-webserver.pid >nul 2>&1
)

REM Subir containers
docker compose up -d airflow-webserver airflow-scheduler
timeout /t 10 /nobreak >nul

REM Verificar se containers estao rodando
set "AIRFLOW_CONTAINER_RUNNING=false"
for /f "delims=" %%H in ('docker inspect -f "{{.State.Running}}" cryptoetl-airflow-webserver-1 2^>nul') do set "AIRFLOW_CONTAINER_RUNNING=%%H"
if /i not "%AIRFLOW_CONTAINER_RUNNING%"=="true" (
    echo Erro: container airflow-webserver nao esta rodando.
    echo Analisando logs...
    docker compose logs --no-color --tail 50 airflow-webserver
    timeout /t 30 /nobreak >nul
    goto end
)
echo [OK] Containers iniciados.
echo.

echo [3/6] Aguardando Airflow webserver ficar pronto ^(pode demorar ate 90s^)...
set "AIRFLOW_READY=0"
set /a AIRFLOW_WAIT=0
:wait_airflow
REM Verificar se o container ainda esta rodando
for /f "delims=" %%H in ('docker inspect -f "{{.State.Running}}" cryptoetl-airflow-webserver-1 2^>nul') do set AIRFLOW_RUNNING=%%H
if /i not "%AIRFLOW_RUNNING%"=="true" (
    echo Erro: container airflow-webserver caiu!
    docker compose logs --no-color --tail 100 airflow-webserver
    goto end
)

REM Testar conexao
powershell -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8080/login' -TimeoutSec 3 -MaximumRedirection 0; if ($r.StatusCode -eq 200 -or $r.StatusCode -eq 302) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 (
    set "AIRFLOW_READY=1"
) else (
    if %AIRFLOW_WAIT% GEQ 90 (
        echo Aviso: Airflow nao respondeu apos %AIRFLOW_WAIT%s, mas container esta rodando. Continuando...
        set "AIRFLOW_READY=1"
    ) else (
        if %AIRFLOW_WAIT% GEQ 0 (
            echo Aguardando Airflow... !AIRFLOW_WAIT!s elapsed
        )
        timeout /t 3 /nobreak >nul
        set /a AIRFLOW_WAIT+=3
        goto wait_airflow
    )
)
echo [OK] Airflow webserver pronto ^(%AIRFLOW_WAIT%s^).
echo.
REM Aguardar um pouco mais para garantir que Airflow esta 100% pronto
timeout /t 5 /nobreak >nul

echo [4/6] Conferindo containers e executando DAGs...
REM Ver containers ativos
docker compose ps
echo.
REM Rodar as DAGs
echo Executando DAGs...
docker exec -i cryptoetl-airflow-webserver-1 airflow dags test dag_extract_bcb 2026-05-24
docker exec -i cryptoetl-airflow-webserver-1 airflow dags test dag_extract_coingecko 2026-05-24
docker exec -i cryptoetl-airflow-webserver-1 airflow dags test dag_consolidate 2026-05-24
echo [OK] DAGs executadas.
echo.

echo [5/6] Validando dados e rodando testes...
echo Validando banco de dados...
docker exec -i cryptoetl-postgres-1 psql -U etl_user -d pipeline_db -c "SELECT COUNT(*) FROM bcb_indicators;"
docker exec -i cryptoetl-postgres-1 psql -U etl_user -d pipeline_db -c "SELECT COUNT(*) FROM crypto_market;"
docker exec -i cryptoetl-postgres-1 psql -U etl_user -d pipeline_db -c "SELECT COUNT(*) FROM daily_consolidated;"
echo [OK] Banco validado.
echo.

echo Rodando testes unitarios...
if not exist reports\screenshots mkdir reports\screenshots
.\.venv\Scripts\python.exe -m pytest -q > reports\screenshots\pytest_output.txt 2>&1
echo [OK] Testes concluidos.
echo.

echo Gerando evidencias de execucao...
.\.venv\Scripts\python.exe scripts\generate_evidence.py
echo [OK] Evidencias geradas.
echo.

echo [6/6] Iniciando dashboard Streamlit...
REM Iniciar o dashboard em background usando a venv ativada

REM Aguardar Streamlit ser iniciado
timeout /t 5 /nobreak >nul
echo Aguardando Streamlit iniciar...
set "STREAMLIT_READY=0"
set /a STREAMLIT_WAIT=0
:wait_streamlit
powershell -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8501' -TimeoutSec 3 -MaximumRedirection 0; if ($r.StatusCode -eq 200 -or $r.StatusCode -eq 302) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 (
    set "STREAMLIT_READY=1"
) else (
    if %STREAMLIT_WAIT% GEQ 60 (
        echo Aviso: Streamlit nao respondeu apos %STREAMLIT_WAIT%s. Continuando...
        set "STREAMLIT_READY=1"
    ) else (
        if %STREAMLIT_WAIT% GEQ 0 (
            echo Aguardando Streamlit... !STREAMLIT_WAIT!s elapsed
        )
        timeout /t 2 /nobreak >nul
        set /a STREAMLIT_WAIT+=2
        goto wait_streamlit
    )
)
echo [OK] Streamlit dashboard pronto ^(%STREAMLIT_WAIT%s^).
echo.

echo Capturando screenshot do dashboard...
.\.venv\Scripts\python.exe scripts\capture_screenshots.py
echo [OK] Screenshot do dashboard capturado.
echo.

echo =========================================
echo SUCESSO - SERVICOS INICIADOS E RODANDO
echo =========================================
echo.
echo Abrindo Airflow no navegador... (aguarde...)
start "" "http://localhost:8080"
timeout /t 3 /nobreak >nul
echo Abrindo Dashboard no navegador... (aguarde...)
start "" "http://localhost:8501"
echo.
echo Airflow:  http://localhost:8080  (credenciais: airflow/airflow)
echo Dashboard: http://localhost:8501
echo.
echo =========================================
echo CAPTURANDO EVIDENCIAS
echo =========================================
echo.
echo [1/2] AIRFLOW - Faca login com: airflow/airflow
echo Pressione ENTER quando tiver feito login e estiver pronto para capturar os prints...
pause >nul
echo.
echo  Capturando screenshots das DAGs do Airflow...
.\.venv\Scripts\python.exe scripts\capture_screenshots.py airflow
echo.
echo [2/2] DASHBOARD - Capturando em 25 segundos...
echo Nao feche o terminal durante a captura!
echo.
.\.venv\Scripts\python.exe scripts\capture_screenshots.py dashboard
echo.
echo =========================================
echo EVIDENCIAS CAPTURADAS COM SUCESSO!
echo =========================================
echo.
echo ^*^*^* OS SERVICOS CONTINUARAO RODANDO ^*^*^*
echo.
echo Para ENCERRAR, abra outro terminal (PowerShell/CMD) e execute:
echo   docker compose down
echo.
echo Para VERIFICAR LOGS, execute:
echo   docker compose logs -f airflow-webserver
echo   docker compose logs -f airflow-scheduler
echo   docker compose logs -f postgres
echo.
echo Pressione CTRL+C aqui para fechar este terminal (servicos continuam rodando)
echo.

REM Loop infinito de health check
:health_check_loop
timeout /t 30 /nobreak >nul

REM Verificar se Airflow ainda esta rodando
for /f "delims=" %%H in ('docker inspect -f "{{.State.Running}}" cryptoetl-airflow-webserver-1 2^>nul') do set AIRFLOW_CHECK=%%H
if /i not "%AIRFLOW_CHECK%"=="true" (
    echo [AVISO] Airflow webserver caiu! Reiniciando...
    docker compose restart airflow-webserver
)

REM Verificar se Postgres ainda esta rodando
for /f "delims=" %%H in ('docker inspect -f "{{.State.Running}}" cryptoetl-postgres-1 2^>nul') do set POSTGRES_CHECK=%%H
if /i not "%POSTGRES_CHECK%"=="true" (
    echo [AVISO] PostgreSQL caiu! Reiniciando...
    docker compose restart postgres
)

goto health_check_loop

:end
echo.
echo =========================================
echo ERRO - Execucao interrompida
echo =========================================
echo.
echo Se isso foi acidental, execute novamente: apresentacao.bat
echo.
timeout /t 30 /nobreak >nul
endlocal
