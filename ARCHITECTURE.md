# Vector Search Architecture

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                     (Browser - index.html)                       │
└─────────────────────────────────────────────────────────────────┘
                                ↕
                        HTTP Requests
                                ↕
┌─────────────────────────────────────────────────────────────────┐
│                       FLASK APPLICATION                          │
│                          (app.py)                                │
│                                                                   │
│  Endpoints:                                                       │
│  • POST /search           - Vector similarity search             │
│  • GET  /search/stats     - Embeddings statistics                │
│  • POST /news/sync        - Sync news from Massive API           │
│  • POST /watchlist        - Manage ticker watchlist              │
│                                                                   │
│  Components:                                                      │
│  • SentenceTransformer    - Generate query embeddings            │
│  • lakebase.py            - Database connection layer            │
│  • massive_client.py      - External API client                  │
└─────────────────────────────────────────────────────────────────┘
                                ↕
                    psycopg2 / PostgreSQL
                                ↕
┌─────────────────────────────────────────────────────────────────┐
│                    LAKEBASE (Postgres)                           │
│                  with pgvector extension                          │
│                                                                   │
│  Tables:                                                          │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  ticker_news_documents                                  │     │
│  │  • Raw news articles                                    │     │
│  │  • Full metadata (title, description, sentiment...)     │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  ticker_news_embeddings                                 │     │
│  │  • Document-level vectors (384-dim)                     │     │
│  │  • HNSW index for fast search                           │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  ticker_news_chunk_embeddings                           │     │
│  │  • Chunk-level vectors (384-dim)                        │     │
│  │  • HNSW index for fast search                           │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  watchlist                                              │     │
│  │  • User-tracked tickers                                 │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                                ↕
                    Spark / Databricks Notebook
                                ↕
┌─────────────────────────────────────────────────────────────────┐
│                      EMBEDDING PIPELINE                          │
│              (ingest_ticker_news_embeddings)                     │
│                                                                   │
│  Process:                                                         │
│  1. Read watchlist → get tickers                                 │
│  2. Fetch news from Massive API                                  │
│  3. Store raw docs in ticker_news_documents                      │
│  4. Generate document embeddings                                 │
│  5. Store in ticker_news_embeddings                              │
│  6. Chunk articles into passages                                 │
│  7. Generate chunk embeddings                                    │
│  8. Store in ticker_news_chunk_embeddings                        │
└─────────────────────────────────────────────────────────────────┘
                                ↕
                          External API
                                ↕
┌─────────────────────────────────────────────────────────────────┐
│                        MASSIVE API                               │
│                    (Financial News Data)                         │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Data Flow

### 1. Data Ingestion Flow

```
User adds ticker     Notebook triggers    Massive API call
  to watchlist    →      ETL process    →    returns news
       ↓                     ↓                     ↓
   Lakebase           Read watchlist         Parse articles
   watchlist     →     tickers from      →    and store in
    table              watchlist              ticker_news_
                                              documents
```

### 2. Embedding Generation Flow

```
Raw news in          Load embedding       Generate vectors
  documents      →         model       →    for each doc
    table          (SentenceTransformer)         ↓
                                          Store in
                                       embeddings table
                                              ↓
                                        Create HNSW
                                          index
```

### 3. Search Query Flow

```
User enters         Generate query       pgvector cosine
  search text   →      embedding     →    similarity
      ↓                    ↓                search
Query embedding      [0.02, -0.15...]       ↓
                                       Find top-k
                                        similar
                                       documents
                                            ↓
                                      Join with
                                    raw documents
                                      for metadata
                                            ↓
                                       Return to
                                          UI
```

## 🔍 Search Process Detail

### Step-by-Step Search

**1. User Input**
```javascript
{
  "prompt": "AI developments in tech",
  "limit": 10,
  "ticker": "MSFT"  // optional
}
```

**2. Backend Processing**
```python
# Load model (cached after first use)
model = SentenceTransformer("all-MiniLM-L6-v2")

# Generate embedding
query_vec = model.encode("AI developments in tech")
# → [0.023, -0.145, 0.678, ..., 0.234]  (384 numbers)
```

**3. Database Query**
```sql
-- Document-level search
SELECT 
    e.id, e.ticker, e.title, d.description, d.sentiment,
    1 - (e.embedding <=> '[0.023,-0.145,...]') AS similarity
FROM ticker_news_embeddings e
LEFT JOIN ticker_news_documents d ON e.id = d.id
WHERE e.ticker = 'MSFT'  -- optional filter
ORDER BY e.embedding <=> '[0.023,-0.145,...]'
LIMIT 10;

-- Chunk-level search (similar)
SELECT 
    c.id, c.chunk_text, c.chunk_index, d.title,
    1 - (c.embedding <=> '[0.023,-0.145,...]') AS similarity
FROM ticker_news_chunk_embeddings c
LEFT JOIN ticker_news_documents d ON c.article_id = d.id
WHERE c.ticker = 'MSFT'
ORDER BY c.embedding <=> '[0.023,-0.145,...]'
LIMIT 10;
```

**4. Result Ranking**
```
Documents sorted by similarity (0-1):
1. "Microsoft's new AI tools..." - 0.87
2. "Tech giants embrace AI..." - 0.82
3. "AI startups raise funding..." - 0.78
...

Chunks sorted by similarity:
1. "The company unveiled AI features..." - 0.91
2. "Microsoft invested $10B in OpenAI..." - 0.89
...
```

**5. Response**
```json
{
  "documents": [...],  // Top 10 docs with metadata
  "chunks": [...],     // Top 10 chunks with text
  "similarity_scores": [0.87, 0.82, 0.78, ...]
}
```

## 🗄️ Table Relationships

```
ticker_news_documents (1)
         ↓
         ↓ (one-to-one)
         ↓
ticker_news_embeddings (1)
    id → id


ticker_news_documents (1)
         ↓
         ↓ (one-to-many)
         ↓
ticker_news_chunk_embeddings (N)
    id → article_id
```

**Example**:
```
Article: "Microsoft announces new AI features..."
    ↓
Document embedding (1):
    Vector: [0.02, -0.15, 0.68, ...]
    
Chunks (4):
    Chunk 0: "Microsoft announces..." → [0.01, -0.14, ...]
    Chunk 1: "The new features include..." → [0.03, -0.16, ...]
    Chunk 2: "CEO Satya Nadella said..." → [0.02, -0.15, ...]
    Chunk 3: "Available starting..." → [0.02, -0.13, ...]
```

## ⚡ Performance Characteristics

### Query Latency Breakdown

```
Total: ~200ms (after model loaded)
├─ Embedding generation: ~100ms
│  └─ SentenceTransformer encode
├─ Database query: ~80ms
│  ├─ Document search: ~40ms (HNSW index)
│  └─ Chunk search: ~40ms (HNSW index)
└─ Response formatting: ~20ms
```

### Scalability

**Current Setup** (small scale):
- ~1,000 documents
- ~5,000 chunks
- Search time: ~200ms

**Medium Scale**:
- ~100,000 documents
- ~500,000 chunks
- Search time: ~500ms (with HNSW)

**Large Scale**:
- ~1M documents
- ~5M chunks
- Search time: ~1-2s (with HNSW)
- May need sharding or approximate search tuning
