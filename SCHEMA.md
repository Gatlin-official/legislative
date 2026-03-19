# PostgreSQL + pgvector Schema

## Database Setup

### Initial SQL Commands

```sql
-- Create database
CREATE DATABASE legislative_db;

-- Connect to database
\c legislative_db

-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extensions
\dx
```

## Tables

### document_chunks

Stores document chunks, embeddings, and metadata.

```sql
CREATE TABLE document_chunks (
    -- Primary key
    id SERIAL PRIMARY KEY,
    
    -- Document reference
    doc_id VARCHAR(255) NOT NULL,
    chunk_index INTEGER NOT NULL,
    
    -- Content
    text TEXT NOT NULL,
    
    -- Vector embedding (384-dimensional for sentence-transformers/all-MiniLM-L6-v2)
    embedding vector(384),
    
    -- Metadata as JSON (source, section_title, token_count, etc.)
    metadata JSONB NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(doc_id, chunk_index),
    CONSTRAINT valid_chunk_index CHECK (chunk_index >= 0)
);
```

## Indexes

Optimize for common query patterns:

### Vector Similarity Search (IVFFlat)
```sql
-- Fast approximate nearest neighbor search
CREATE INDEX idx_embedding_cosine 
ON document_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Note: Adjust 'lists' parameter based on dataset size:
-- - Small datasets (< 10k): lists = 50
-- - Medium datasets (10k-100k): lists = 100
-- - Large datasets (100k+): lists = 1000
```

### Document ID Lookup
```sql
-- Fast filtering by document
CREATE INDEX idx_doc_id 
ON document_chunks(doc_id);
```

### Chunk Ordering
```sql
-- Fast ordering within a document
CREATE INDEX idx_doc_id_chunk_index 
ON document_chunks(doc_id, chunk_index);
```

### Full-Text Search (Optional)
```sql
-- For text search capability (separate from semantic search)
CREATE INDEX idx_text_fts 
ON document_chunks USING GIN(to_tsvector('english', text));
```

## Queries (via SQLAlchemy ORM)

### Add Chunks
```python
from vector_store import DocumentChunk

# Create chunk objects
chunks = [
    DocumentChunk(
        doc_id="doc-123",
        chunk_index=0,
        text="Your text here",
        embedding=embedding_vector,
        metadata={"source": "file.pdf", "token_count": 150}
    ),
    # ... more chunks
]

session.add_all(chunks)
session.commit()
```

### Semantic Search
```sql
-- Find 5 most similar chunks for a query
SELECT 
    text,
    metadata,
    (1 - (embedding <=> $1)) as similarity_score
FROM document_chunks
WHERE doc_id = 'doc-123'
ORDER BY embedding <=> $1
LIMIT 5;

-- $1 = query embedding vector
```

**Via Python:**
```python
from sqlalchemy import func

results = session.query(
    DocumentChunk.text,
    DocumentChunk.metadata,
    (1 - (DocumentChunk.embedding.op("<=>")(...)).label("similarity")
).filter(
    DocumentChunk.doc_id == "doc-123"
).order_by(
    DocumentChunk.embedding.op("<=>")(...)
).limit(5).all()
```

### List Document Stats
```sql
SELECT 
    doc_id,
    COUNT(*) as chunk_count,
    MIN(created_at) as created_at,
    MAX(updated_at) as updated_at
FROM document_chunks
GROUP BY doc_id;
```

## Maintenance

### Monitoring

```sql
-- Check table size
SELECT 
    pg_size_pretty(pg_total_relation_size('document_chunks')) as size;

-- Check index sizes
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_indexes 
WHERE tablename = 'document_chunks';

-- Check row counts
SELECT 
    doc_id,
    COUNT(*) as chunks
FROM document_chunks
GROUP BY doc_id;
```

### Maintenance Tasks

```sql
-- Rebuild vector index (after many insertions/deletions)
REINDEX INDEX idx_embedding_cosine;

-- Vacuum table (reclaim space)
VACUUM ANALYZE document_chunks;

-- Check index health
EXPLAIN (ANALYZE) 
SELECT * FROM document_chunks 
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector 
LIMIT 5;
```

## Performance Tuning

### PostgreSQL Config (`postgresql.conf`)

```ini
# For better vector search performance
shared_buffers = '4GB'           # 25% of RAM
effective_cache_size = '12GB'    # 75% of RAM
work_mem = '100MB'               # shared_buffers / max_connections
maintenance_work_mem = '1GB'

# For faster indexing during bulk loads
random_page_cost = 1.1           # If using SSD
```

### Vector Index Tuning

```sql
-- Smaller lists = faster build, slower search
-- Larger lists = slower build, faster search
-- Default (100) is balanced for most cases

-- For faster index builds (lots of inserts):
CREATE INDEX CONCURRENTLY idx_embedding_fast
ON document_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);

-- For better search accuracy (lots of queries):
CREATE INDEX CONCURRENTLY idx_embedding_accurate
ON document_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 1000);
```

## Backup & Recovery

### Backup

```bash
# Full database backup
pg_dump -U postgres -d legislative_db > backup.sql

# Compressed backup
pg_dump -U postgres -d legislative_db | gzip > backup.sql.gz
```

### Restore

```bash
# Restore from SQL file
psql -U postgres -d legislative_db < backup.sql

# Restore from compressed backup
gunzip -c backup.sql.gz | psql -U postgres -d legislative_db
```

## Scaling Considerations

### Single Machine (< 1M chunks)
- Current setup sufficient
- 16GB RAM recommended
- SSD storage required for performance

### Distributed Setup (> 1M chunks)

```sql
-- Use PostgreSQL streaming replication
-- Setup read replicas for queries
-- Use pgBouncer connection pooling
-- Consider Redis caching layer
```

### Horizontal Scaling (> 10M chunks)

- Shard by `doc_id` across multiple PostgreSQL instances
- Use load balancer for connection distribution
- Consider managed PostgreSQL (AWS RDS, Azure Database)

## SQL Reference

### Connection URI

```
postgresql://[user[:password]]@[host][:port]/[database]

Examples:
postgresql://postgres:password@localhost:5432/legislative_db
postgresql://postgres@/legislative_db              (Unix socket)
```

### Useful Psql Commands

```bash
# Connect
psql -U postgres -d legislative_db -h localhost

# Inside psql
\dt              # List tables
\di              # List indexes
\dx              # List extensions
\db              # List databases
\df              # List functions
\x               # Toggle expanded output
\timing          # Toggle query timing
\q               # Quit

# SQL info
\d document_chunks           # Describe table
\d+ document_chunks          # With extra info
```

---

**For more info on pgvector:** https://github.com/pgvector/pgvector
**PostgreSQL docs:** https://www.postgresql.org/docs/current/
