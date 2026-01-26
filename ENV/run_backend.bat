@echo off
REM Arranca solo el backend desde ENV
setlocal
cd /d "%~dp0"

python --version >NUL 2>&1
if errorlevel 1 (
    echo Python no esta en PATH. Instala desde https://www.python.org/downloads/ Marca Add Python to PATH.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo No se encontro .venv. Ejecuta primero setup_env.bat
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

endlocal
