@echo off
echo ==============================================
echo     FOOTBALL ANALYTICS - SISTEMA COMPLETO
echo ==============================================
echo.
echo Iniciando Backend (API) na porta 8000...
start "Football Analytics API" cmd /k "python main_basic.py"
echo.
echo Aguardando 3 segundos...
timeout /t 3 /nobreak > nul
echo.
echo Iniciando Frontend na porta 3000...
start "Football Analytics Frontend" cmd /k "cd frontend && npm run dev"
echo.
echo ==============================================
echo   SISTEMA INICIADO COM SUCESSO!
echo ==============================================
echo.
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000
echo.
echo Pressione qualquer tecla para fechar...
pause > nul 