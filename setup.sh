#!/bin/bash
# setup.sh - One-command setup for Ollama + backend

set -e

echo "Setup Script - AI Legislative Analyzer"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    echo "Please install Python 3.9+ from https://www.python.org/"
    exit 1
fi
echo -e "${GREEN}OK Python $(python3 --version)${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}[X] Node.js not found${NC}"
    echo "Please install Node.js 16+ from https://nodejs.org/"
    exit 1
fi
echo -e "${GREEN}OK Node.js $(node --version)${NC}"

# Check Ollama
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}[!] Ollama not found${NC}"
    echo "Please install Ollama from https://ollama.ai"
    echo "Then re-run this script."
    exit 1
fi
echo -e "${GREEN}OK Ollama found${NC}"

echo ""
echo "Installing Python dependencies..."

cd backend

# Create virtual environment
python3 -m venv venv

# Activate venv
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install requirements
pip install -q -r requirements.txt
echo -e "${GREEN}OK Python packages installed${NC}"

echo ""
echo "Pulling Llama 3.1 model..."

# Pull Llama model (background, might take several minutes)
ollama pull llama3.1:8b &
OLLAMA_PID=$!

echo -e "${YELLOW}  Model loading in background (this may take 5-10 minutes first time)${NC}"
echo -e "${YELLOW}  Size: ~5GB${NC}"

echo ""
echo "Setting up Frontend..."

cd ../frontend
npm install -q
echo -e "${GREEN}OK Frontend dependencies installed${NC}"

echo ""
echo "Creating .env file..."

# Create .env if it doesn't exist
if [ ! -f ../.env ]; then
    cat > ../.env << EOF
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.1:8b

# Backend
BACKEND_PORT=8000
ENVIRONMENT=development
COMPRESSION_TARGET=0.4
EOF
    echo -e "${GREEN}OK .env created${NC}"
else
    echo -e "${GREEN}OK .env already exists${NC}"
fi

# Wait for Ollama model to complete
wait $OLLAMA_PID 2>/dev/null || true

echo ""
echo "======================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "======================================"
echo ""
echo "To start the application:"
echo ""
echo "Terminal 1 - Backend:"
echo "  cd backend"
echo "  source venv/bin/activate  # or venv\Scripts\activate on Windows"
echo "  python main.py"
echo ""
echo "Terminal 2 - Frontend:"
echo "  cd frontend"
echo "  npm run dev"
echo ""
echo "Terminal 3 - Ollama (if not running):"
echo "  ollama serve"
echo ""
echo "Then open http://localhost:5173 in your browser!"
echo ""
