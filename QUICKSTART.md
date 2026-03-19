# QUICK START GUIDE

## 🚀 Get Running in 5 Minutes

### Prerequisites
- PostgreSQL 13+ with pgvector extension
- Ollama running with Llama 3.1:8b model
- Python 3.9+, Node.js 16+

### 1. Setup PostgreSQL

**Install PostgreSQL and pgvector extension:**

```bash
# macOS (Homebrew)
brew install postgresql@15
brew services start postgresql@15

# Windows
# Download from https://www.postgresql.org/download/windows/

# Linux (Ubuntu/Debian)
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Create database:**
```bash
psql -U postgres

# Inside psql:
CREATE DATABASE legislative_db;
CREATE EXTENSION vector;
\q
```

### 2. Setup Ollama & Llama 3.1:8b

**Install Ollama:**
```bash
# From https://ollama.ai
# Download and install for your OS
```

**Pull Llama 3.1:8b model:**
```bash
ollama pull llama3.1:8b
```

**Start Ollama server:**
```bash
ollama serve
# Runs on http://localhost:11434
```

### 3. Setup Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Configure Backend

**Create backend/.env:**
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/legislative_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=legislative_db
DB_USER=postgres
DB_PASSWORD=password

OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.1:8b

BACKEND_PORT=8000
ENVIRONMENT=development
COMPRESSION_TARGET=0.4
```

### 5. Start Backend

```bash
python main.py
# Runs on http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 6. Setup Frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

### 7. Upload a Test Document

1. Go to http://localhost:3000
2. Drag and drop a PDF or DOCX file
3. Wait for ingestion (embeddings → PostgreSQL)
4. Click document to view

---

## ✨ Key Changes from Original Version

| Feature | Before | Now |
|---------|--------|-----|
| Vector DB | ChromaDB (local) | PostgreSQL + pgvector |
| LLM | OpenAI API | Ollama + Llama 3.1:8b |
| Cost | $$ API calls | $0 (local) |
| Speed | Network latency | Local inference |
| Privacy | Data to OpenAI | All local ✅ |

---

## 📊 Watch Token Compression in Action

Every response shows:
- ✅ **Tokens saved:** Exact count removed
- ✅ **Compression %:** 40%+ efficiency (green badge)
- ✅ **Cost savings:** Now $0, always free! 🎉

---

## 🔌 API Quick Reference

```bash
# Check health (shows local LLM)
curl http://localhost:8000/health

# Upload a document
curl -X POST http://localhost:8000/upload \
  -F "file=@your-bill.pdf"

# Ask a question (uses local Llama)
curl -X POST http://localhost:8000/ask/doc-123 \
  -H "Content-Type: application/json" \
  -d '{"doc_id": "doc-123", "question": "Who is eligible?"}'

# Get summary (MapReduce with Llama)
curl -X POST http://localhost:8000/summarize/doc-123 \
  -H "Content-Type: application/json" \
  -d '{"doc_id": "doc-123", "style": "citizen"}'
```

---

## 🐛 Troubleshooting

**Ollama connection refused?**
- Ensure `ollama serve` is running in another terminal
- Check: `curl http://localhost:11434/api/tags`

**PostgreSQL connection error?**
- Verify database is running: `psql -U postgres -d legislative_db`
- Check `.env` credentials match your setup
- Ensure pgvector extension installed: `psql -d legislative_db -c "CREATE EXTENSION IF NOT EXISTS vector"`

**Embedding errors?**
- Pull model again: `ollama pull llama3.1:8b`
- Check disk space (model is ~5GB)

**Slow queries?**
- First run builds indexes automatically
- Subsequent queries are much faster
- Run: `psql -d legislative_db -c "CREATE INDEX IF NOT EXISTS idx_doc_id ON document_chunks(doc_id)"`

---

## 🚀 Production Tips

For scaling beyond local development:

1. **PostgreSQL tuning:**
   ```bash
   # max_connections, shared_buffers, etc.
   # See PostgreSQL docs for server class
   ```

2. **Vector search optimization:**
   ```sql
   -- Create index for faster similarity search
   CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops)
   WITH (lists = 100);
   ```

3. **Multi-node Ollama:**
   - Run Ollama on separate GPU server
   - Update `OLLAMA_BASE_URL` to point to server

---

Enjoy local, free, private legislative analysis! 🇮🇳 All locally under your control.
