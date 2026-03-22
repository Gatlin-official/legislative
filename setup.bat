@echo off
REM setup.bat - One-command setup for Ollama + backend (Windows)

echo.
echo Setup Script - AI Legislative Analyzer (Windows)
echo ==================================================
echo.

setlocal enabledelayedexpansion

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python not found
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION%

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [X] Node.js not found
    echo Please install Node.js 16+ from https://nodejs.org/
    pause
    exit /b 1
)
for /f %%i in ('node --version') do set NODE_VERSION=%%i
echo [OK] Node.js %NODE_VERSION%

REM Check Ollama
where ollama >nul 2>&1
if errorlevel 1 (
    echo [!] Ollama not found in PATH
    echo Please install Ollama from https://ollama.ai
    echo Then re-run this script.
    pause
    exit /b 1
)
echo [OK] Ollama found

echo.
echo Installing Python dependencies...

cd /d "%~dp0backend"

REM Create virtual environment
python -m venv venv
call venv\Scripts\activate.bat

REM Install requirements
pip install -q -r requirements.txt
echo [OK] Python packages installed

echo.
echo Pulling Llama 3.1 model...

REM Pull Llama model
call ollama pull llama3.1:8b

echo.
echo Setting up Frontend...

cd /d "%~dp0frontend"
call npm install
echo [OK] Frontend dependencies installed

echo.
echo Creating .env file...

if not exist "..\\.env" (
    (
        echo # Ollama
        echo OLLAMA_BASE_URL=http://localhost:11434
        echo LLM_MODEL=llama3.1:8b
        echo.
        echo # Backend
        echo BACKEND_PORT=8000
        echo ENVIRONMENT=development
        echo COMPRESSION_TARGET=0.4
    ) > ..\\.env
    echo [OK] .env created
) else (
    echo [OK] .env already exists
)

echo.
echo ==================================================
echo Setup Complete!
echo ==================================================
echo.
echo To start the application:
echo.
echo Terminal 1 - Backend:
echo   cd backend
echo   venv\Scripts\activate
echo   python main.py
echo.
echo Terminal 2 - Frontend:
echo   cd frontend
echo   npm run dev
echo.
echo Terminal 3 - Ollama (if not running):
echo   ollama serve
echo.
echo Then open http://localhost:5173 in your browser!
echo.
pause
