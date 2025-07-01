@echo off
echo ===============================================
echo    INICIANDO SPORTS DATA API (BACKEND)
echo ===============================================
echo.
echo [INFO] Verificando ambiente...

REM Verificar se Python está instalado
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Python nao encontrado! Instale Python 3.8+ e tente novamente.
    goto :end
)

echo [OK] Python encontrado!
echo [INFO] Iniciando API na porta 8000...
echo.
echo -----------------------------------------------
echo A API PRECISA ESTAR RODANDO PARA O N8N FUNCIONAR
echo -----------------------------------------------
echo.
echo Pressione CTRL+C para encerrar a API quando terminar.
echo.

REM Iniciar a API usando o arquivo main.py
python main.py

:end
pause 