@echo off
if "%~1" neq "KEEP" (
    cmd /k "%~f0" KEEP
    exit /b
)
REM Inicializa el entorno dentro de ENV: crea .venv, instala requisitos y copia .env si falta.
setlocal
set "SETUP_OK=1"
cd /d "%~dp0"

echo === Comprobando Python en PATH ===
for /f "delims=" %%I in ('python --version 2^>^&1') do set "SYS_PY=%%I"
if not defined SYS_PY set "SYS_PY=Python no encontrado"
echo Python detectado: %SYS_PY%
set "VENV_DIR=.venv"
if exist ".venv_path" (
    for /f "usebackq delims=" %%I in (".venv_path") do set "VENV_DIR=%%I"
)
set "PY_CMD=python"
py -3.12 -V >NUL 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3.12"
) else (
    py -3.11 -V >NUL 2>&1
    if not errorlevel 1 set "PY_CMD=py -3.11"
)
%PY_CMD% --version >NUL 2>&1
if errorlevel 1 (
    echo Python no esta instalado o no esta en PATH.
    echo Descarga Python 3.12 y marca "Add Python to PATH".
    echo Web: https://www.python.org/downloads/
    echo.
    echo Si tienes Windows 10/11 puedes instalarlo desde la Microsoft Store o con winget.
    echo.
    echo Abriendo la pagina de descarga...
    start "" "https://www.python.org/downloads/"
    pause
    set "SETUP_OK=0"
    goto :end
)
%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info[:2] <= (3,12) else 1)" >NUL 2>&1
if errorlevel 1 (
    echo Esta instalacion requiere Python 3.11 o 3.12 para evitar errores con numpy/streamlit.
    echo Instala Python 3.12 y vuelve a ejecutar este script.
    pause
    set "SETUP_OK=0"
    goto :end
)
for /f "delims=" %%I in ('%PY_CMD% -c "import sys; print(sys.executable)"') do set "PY_EXE=%%I"
if not defined PY_EXE (
    echo No se pudo detectar el ejecutable de Python.
    pause
    set "SETUP_OK=0"
    goto :end
)

echo === Creando entorno virtual si no existe (%VENV_DIR%) ===
set "ACTIVATE_BAT=%VENV_DIR%\Scripts\activate.bat"
if exist "%ACTIVATE_BAT%" goto :venv_ready
"%PY_EXE%" -m venv "%VENV_DIR%"
if errorlevel 1 goto :venv_fallback
goto :venv_ready

:venv_fallback
echo No se pudo crear la .venv en esta ruta (permiso denegado).
echo Intentando en una ruta de usuario...
set "VENV_DIR=%LOCALAPPDATA%\ORBE_ENV\.venv"
if not exist "%LOCALAPPDATA%\ORBE_ENV" mkdir "%LOCALAPPDATA%\ORBE_ENV"
"%PY_EXE%" -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo Error creando la .venv en %VENV_DIR%
    pause
    set "SETUP_OK=0"
    goto :end
)
echo %VENV_DIR%> .venv_path

:venv_ready

echo === Activando entorno virtual ===
set "ACTIVATE_BAT=%VENV_DIR%\Scripts\activate.bat"
call "%ACTIVATE_BAT%"
if errorlevel 1 (
    echo No se pudo activar la .venv en %VENV_DIR%
    pause
    set "SETUP_OK=0"
    goto :end
)

echo === Verificando Python del entorno ===
for /f "delims=" %%I in ('where python 2^>NUL') do (
    set "PY_PATH=%%I"
    goto :py_found
)
:py_found
if not defined PY_PATH (
    echo No se encontro Python activo en la .venv.
    pause
    set "SETUP_OK=0"
    goto :end
)
echo Python activo: %PY_PATH%

echo === Comprobando version de Python del entorno ===
python -c "import sys; raise SystemExit(0 if sys.version_info[:2] <= (3,12) else 1)" >NUL 2>&1
if errorlevel 1 (
    echo La .venv actual no es compatible. Usa Python 3.11 o 3.12.
    echo Borra la carpeta .venv y ejecuta de nuevo este script.
    python --version
    pause
    set "SETUP_OK=0"
    goto :end
)

echo === Instalando dependencias (forzado) ===
set PYTHONNOUSERSITE=1
set PIP_NO_WARN_SCRIPT_LOCATION=1
set PIP_DISABLE_PIP_VERSION_CHECK=1
"%VENV_DIR%\\Scripts\\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo Error actualizando pip dentro de la .venv.
    pause
    set "SETUP_OK=0"
    goto :end
)
"%VENV_DIR%\\Scripts\\python.exe" -m pip install --upgrade --force-reinstall -r requirements.txt
if errorlevel 1 (
    echo Error instalando dependencias en la .venv.
    pause
    set "SETUP_OK=0"
    goto :end
)

echo === Comprobando .env ===
if not exist ".env" (
    echo No existe .env en ENV. Crea el archivo con URL_SUPABASE y SUPABASE_KEY.
    pause
    set "SETUP_OK=0"
    goto :end
)

echo === Entorno listo. Usa run_all.bat para arrancar backend+frontend. ===
pause
:end
if "%SETUP_OK%"=="0" (
    echo === Setup terminado con errores ===
)
endlocal
