@echo off
REM Arranca backend y frontend desde la carpeta ENV
setlocal
cd /d "%~dp0"
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "VENV_DIR=.venv"
if exist "%ROOT%\\.venv_path" (
    set /p VENV_DIR=<"%ROOT%\\.venv_path"
)

python --version >NUL 2>&1
if errorlevel 1 (
    echo Python no esta en PATH. Instala desde https://www.python.org/downloads/ Marca Add Python to PATH.
    pause
    exit /b 1
)

if not exist "%VENV_DIR%\\Scripts\\activate.bat" (
    echo No se encontro la .venv. Ejecutando setup_env.bat...
    call "%ROOT%\\setup_env.bat"
)
if exist "%ROOT%\\.venv_path" (
    set /p VENV_DIR=<"%ROOT%\\.venv_path"
)
if not exist "%VENV_DIR%\\Scripts\\activate.bat" (
    echo No se pudo crear la .venv. Revisa la salida de setup_env.bat
    exit /b 1
)

call "%VENV_DIR%\\Scripts\\activate.bat"

start "backend" cmd /k "cd /d ""%ROOT%"" && uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"
start "streamlit" cmd /k "cd /d ""%ROOT%"" && streamlit run app.py --server.port 8501 --server.address 127.0.0.1"

timeout /t 2 >NUL
start "" "http://localhost:8501"

echo.
echo Backend:   http://localhost:8000
echo Frontend:  http://localhost:8501
echo.
endlocal
