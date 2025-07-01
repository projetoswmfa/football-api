@echo off
title API Sports Data - DADOS 100%% REAIS (Zero Simulacao)
color 0A
echo.
echo ===================================================================
echo  🎯 INICIANDO API SPORTS DATA - DADOS 100%% REAIS (ZERO SIMULACAO)
echo ===================================================================
echo.
echo ✅ Garantias:
echo    - ZERO simulacao
echo    - Dados 100%% reais de APIs confiáveis
echo    - Múltiplas fontes (ESPN, Football-Data, API-Football)
echo    - Validacao rigorosa anti-simulacao
echo.
echo 📡 Endpoints principais:
echo    - GET /matches/live-real (PARTIDAS AO VIVO 100%% REAIS)
echo    - GET /matches/today-real (PARTIDAS DE HOJE 100%% REAIS)
echo    - GET /sports/multi-real (MULTIPLOS ESPORTES 100%% REAIS)
echo.
echo ⚠️  IMPORTANTE: Nenhum dado será simulado!
echo.

echo 🔍 Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python não encontrado! Instale o Python primeiro.
    pause
    exit /b 1
)
echo ✅ Python encontrado

echo.
echo 🔍 Verificando dependências...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Instalando dependências...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Erro ao instalar dependências
        pause
        exit /b 1
    )
)
echo ✅ Dependências OK

echo.
echo 🔍 Verificando módulos de dados reais...
if not exist "scrapers\unified_real_scraper.py" (
    echo ❌ Módulo unified_real_scraper.py não encontrado!
    echo    Execute novamente o setup da API com dados reais.
    pause
    exit /b 1
)
echo ✅ Módulos de dados reais encontrados

echo.
echo 🚀 INICIANDO API COM DADOS 100%% REAIS...
echo    Porta: 8000
echo    Host: localhost
echo    Modo: ZERO SIMULACAO
echo.
echo 📊 URLs importantes:
echo    - Health: http://localhost:8000/health
echo    - Docs: http://localhost:8000/docs
echo    - Live Real: http://localhost:8000/matches/live-real
echo    - Today Real: http://localhost:8000/matches/today-real
echo.
echo 🔄 Para testar os dados reais após iniciar:
echo    python test_real_data.py
echo.
echo ═══════════════════════════════════════════════════════════════════
echo.

REM Iniciar a API
python main.py

echo.
echo ⚠️ API encerrada. Pressione qualquer tecla para sair...
pause >nul 