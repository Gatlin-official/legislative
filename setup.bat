@echo off
REM setup.bat - One-command setup for PostgreSQL + Ollama + backend (Windows)

echo.
echo 🚀 AI Legislative Analyzer - Setup Script (Windows)
echo ====================================================
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
echo ✓ Python %PYTHON_VERSION%

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Node.js not found
    echo Please install Node.js 16+ from https://nodejs.org/
    pause
    exit /b 1
)
for /f %%i in ('node --version') do set NODE_VERSION=%%i
echo ✓ Node.js %NODE_VERSION%

REM Check PostgreSQL
where psql >nul 2>&1
if errorlevel 1 (
    echo ⚠ PostgreSQL not found in PATH
    echo Please install PostgreSQL 13+ from https://www.postgresql.org/download/windows/
    echo Then re-run this script.
    pause
    exit /b 1
)
echo ✓ PostgreSQL found

REM Check Ollama
where ollama >nul 2>&1
if errorlevel 1 (
    echo ⚠ Ollama not found in PATH
    echo Please install Ollama from https://ollama.ai
    echo Then re-run this script.
    pause
    exit /b 1
)
echo ✓ Ollama found

echo.
echo 🗄️  Setting up PostgreSQL...

set DB_NAME=legislative_db
set DB_USER=postgres
if not defined DB_PASSWORD set DB_PASSWORD=postgres

REM Create database (skip errors if exists)
psql -U %DB_USER% -tc "SELECT 1 FROM pg_database WHERE datname = '%DB_NAME%'" | findstr /r "1" >nul
if errorlevel 1 (
    psql -U %DB_USER% -c "CREATE DATABASE %DB_NAME%"
)
echo ✓ Database '%DB_NAME%' ready

REM Enable pgvector extension
psql -U %DB_USER% -d %DB_NAME% -c "CREATE EXTENSION IF NOT EXISTS vector" >nul 2>&1
echo ✓ pgvector extension enabled

echo.
echo 📦 Installing Python dependencies...

cd /d "%~dp0backend"

REM Create virtual environment
python -m venv venv
call venv\Scripts\activate.bat

REM Install requirements
pip install -q -r requirements.txt >nul 2>&1
echo ✓ Python packages installed

echo.
echo 🦙 Pulling Llama 3.1:8b model...
echo    (This may take 5-10 minutes first time - ~5GB download)

REM Pull Llama model
call ollama pull llama3.1:8b

echo.
echo 📚 Setting up Frontend...

cd /d "%~dp0frontend"
call npm install >nul 2>&1
echo ✓ Frontend dependencies installed

echo.
echo 📝 Creating .env file...

if not exist "..\\.env" (
    (
        echo # PostgreSQL
        echo DATABASE_URL=postgresql://%DB_USER%:%DB_PASSWORD%@localhost:5432/%DB_NAME%
        echo DB_HOST=localhost
        echo DB_PORT=5432
        echo DB_NAME=%DB_NAME%
        echo DB_USER=%DB_USER%
        echo DB_PASSWORD=%DB_PASSWORD%
        echo.
        echo # Ollama
        echo OLLAMA_BASE_URL=http://localhost:11434
        echo LLM_MODEL=llama3.1:8b
        echo.
        echo # Backend
        echo BACKEND_PORT=8000
        echo ENVIRONMENT=development
        echo COMPRESSION_TARGET=0.4
    ) > ..\\.env
    echo ✓ .env created
) else (
    echo ✓ .env already exists
)

echo.
echo ====================================================
echo ✅ Setup complete!
echo ====================================================
echo.
echo 🚀 To start the application:
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
echo Then open http://localhost:3000 in your browser!
echo.
echo 📖 Full docs: see README.md and QUICKSTART.md
echo.
pause
