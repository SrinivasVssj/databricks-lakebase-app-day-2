# Vector Search Feature - Complete Guide

## Overview

This application now includes a comprehensive **semantic search** feature that allows you to search news articles using natural language queries. The search uses **vector embeddings** and **cosine similarity** powered by pgvector in Lakebase (Databricks-managed Postgres).

## 🗄️ Lakebase Tables

The application uses the following tables in Lakebase:

### 1. `ticker_news_documents` (Raw News)
**Purpose**: Stores raw news articles fetched from the Massive API

**Schema**:
```sql
CREATE TABLE ticker_news_documents (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    author TEXT,
    article_url TEXT,
    publisher_name TEXT,
    keywords JSONB,
    sentiment TEXT,
    sentiment_reasoning TEXT,
    published_utc TIMESTAMPTZ,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Populated by**: 
- Flask endpoint: `POST /news/sync`
- Notebook: `ingest_ticker_news_embeddings`

### 2. `ticker_news_embeddings` (Document-Level Vectors)
**Purpose**: Stores vector embeddings for entire news articles

**Schema**:
```sql
CREATE TABLE ticker_news_embeddings (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    title TEXT NOT NULL,
    published_utc TIMESTAMPTZ,
    embedding VECTOR(384) NOT NULL,  -- 384-dim for all-MiniLM-L6-v2
    model_name TEXT NOT NULL,
    embedded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- HNSW index for fast similarity search
CREATE INDEX idx_ticker_news_embeddings_embedding
ON ticker_news_embeddings
USING hnsw (embedding vector_cosine_ops);
```

**Populated by**: Notebook `ingest_ticker_news_embeddings`

**Notes**: 
- Each document gets ONE embedding vector
- Used for high-level article matching

### 3. `ticker_news_chunk_embeddings` (Chunk-Level Vectors)
**Purpose**: Stores vector embeddings for article chunks/paragraphs

**Schema**:
```sql
CREATE TABLE ticker_news_chunk_embeddings (
    id TEXT PRIMARY KEY,
    article_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    chunk_index INT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    model_name TEXT NOT NULL,
    embedded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- HNSW index for fast similarity search
CREATE INDEX idx_ticker_news_chunk_embeddings_embedding
ON ticker_news_chunk_embeddings
USING hnsw (embedding vector_cosine_ops);
```

**Populated by**: Notebook `ingest_ticker_news_embeddings`

**Notes**: 
- Each article is split into multiple chunks
- Better for finding specific passages
- More granular than document-level search

### 4. `watchlist` (User Watchlist)
**Purpose**: Tracks stock symbols users are monitoring

**Schema**:
```sql
CREATE TABLE watchlist (
    symbol TEXT NOT NULL,
    email TEXT NOT NULL,
    latest_price NUMERIC,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, email)
);
```

**Populated by**: Flask endpoint `POST /watchlist`

**Used by**: Notebook reads this to determine which tickers to fetch news for

### 5. `massive_records` (Generic API Data)
**Purpose**: Generic storage for Massive API responses

**Schema**:
```sql
CREATE TABLE massive_records (
    id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 🔍 Search Endpoints

### 1. POST `/search` - Semantic Search

**Purpose**: Search news using natural language

**Request**:
```json
{
  "prompt": "What news is there about AI developments?",
  "limit": 10,
  "ticker": "MSFT"  // Optional: filter by ticker
}
```

**Response**:
```json
{
  "prompt": "What news is there about AI developments?",
  "ticker_filter": "MSFT",
  "model": "sentence-transformers/all-MiniLM-L6-v2",
  "results_count": {
    "documents": 5,
    "chunks": 5
  },
  "documents": [
    {
      "id": "abc123",
      "ticker": "MSFT",
      "title": "Microsoft Unveils New AI Tools",
      "description": "Microsoft announced...",
      "author": "Jane Doe",
      "article_url": "https://...",
      "publisher_name": "Tech News",
      "sentiment": "positive",
      "sentiment_reasoning": "Optimistic tone about innovation",
      "published_utc": "2026-08-07T10:00:00Z",
      "similarity_score": 0.87
    }
  ],
  "chunks": [
    {
      "id": "chunk_456",
      "article_id": "abc123",
      "ticker": "MSFT",
      "chunk_index": 2,
      "chunk_text": "The company's new AI features include...",
      "article_title": "Microsoft Unveils New AI Tools",
      "published_utc": "2026-08-07T10:00:00Z",
      "article_url": "https://...",
      "similarity_score": 0.91
    }
  ]
}
```

**Key Features**:
- Searches BOTH document-level and chunk-level embeddings
- Joins with `ticker_news_documents` to get full metadata
- Optional ticker filtering
- Returns similarity scores (0-1, higher = more similar)
- Results ordered by relevance

**SQL Query (Documents)**:
```sql
SELECT 
    e.id,
    e.ticker,
    e.title,
    e.published_utc,
    d.description,
    d.author,
    d.article_url,
    d.publisher_name,
    d.sentiment,
    d.sentiment_reasoning,
    1 - (e.embedding <=> %s::vector) AS similarity_score
FROM ticker_news_embeddings e
LEFT JOIN ticker_news_documents d ON e.id = d.id
WHERE e.ticker = %s  -- Optional filter
ORDER BY e.embedding <=> %s::vector
LIMIT %s
```

### 2. GET `/search/stats` - Search Statistics

**Purpose**: Get information about available data

**Request**: None (GET request)

**Response**:
```json
{
  "total_documents": 150,
  "total_chunks": 892,
  "tickers": [
    {"ticker": "AAPL", "doc_count": 45},
    {"ticker": "GOOGL", "doc_count": 38},
    {"ticker": "MSFT", "doc_count": 67}
  ],
  "date_range": {
    "earliest": "2026-07-15T00:00:00Z",
    "latest": "2026-08-08T00:00:00Z"
  },
  "model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

## 🎨 UI Features

The web interface at `/` includes:

### Search Section
- **Natural language input**: Ask questions or describe topics
- **Optional ticker filter**: Focus search on specific stocks
- **Live results**: Updates as you search
- **Two result views**:
  - **📄 Top Documents**: Full articles ranked by relevance
  - **📝 Top Chunks**: Specific passages that match your query

### Document Display
Each document result shows:
- Article title
- Similarity score (percentage)
- Ticker symbol
- Publication date
- Publisher and author
- Sentiment badge (positive/negative/neutral)
- Article description
- Link to full article

### Chunk Display
Each chunk result shows:
- Source article title
- Chunk number
- Similarity score
- Ticker symbol
- The actual text passage
- Link to full article

### Search Stats
- Total documents and chunks found
- Model used for embeddings
- Active ticker filter (if any)

## 🚀 Setup & Usage

### Prerequisites

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

Required packages:
- `sentence-transformers>=2.2.0` - For generating embeddings
- `torch>=2.0.0` - Required by sentence-transformers
- `psycopg2-binary>=2.9.9` - PostgreSQL driver

2. **Setup Lakebase tables**:
```bash
# Run these SQL scripts in your Lakebase database
sql/01_setup_news_table.sql
sql/02_setup_embeddings_table.sql
sql/03_setup_chunk_embeddings_table.sql
```

3. **Enable pgvector** (run in Lakebase):
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Data Pipeline

**Step 1**: Add tickers to watchlist
```bash
# Via UI or API
curl -X POST http://localhost:8000/watchlist \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'
```

**Step 2**: Fetch news articles
```bash
# Via API
curl -X POST http://localhost:8000/news/sync \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL", "MSFT"], "limit": 50}'
```
This populates `ticker_news_documents`.

**Step 3**: Generate embeddings
Run the notebook: `notebooks/ingest_ticker_news_embeddings`

This notebook:
1. Reads watchlisted tickers
2. Fetches recent news (if not already synced)
3. Generates document embeddings → `ticker_news_embeddings`
4. Splits articles into chunks
5. Generates chunk embeddings → `ticker_news_chunk_embeddings`

**Step 4**: Search!
Navigate to the app homepage and start searching.

## 🔧 Configuration

Environment variables (optional):

```bash
# Embedding model (default: all-MiniLM-L6-v2)
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"

# Table names
EMBEDDINGS_TABLE_NAME="ticker_news_embeddings"
CHUNK_EMBEDDINGS_TABLE_NAME="ticker_news_chunk_embeddings"
NEWS_TABLE_NAME="ticker_news_documents"

# Flask settings
FLASK_RUN_HOST="0.0.0.0"
FLASK_RUN_PORT=8000
```

### Supported Embedding Models

You can change the model by setting `EMBEDDING_MODEL`:

- `sentence-transformers/all-MiniLM-L6-v2` (384 dims) - **Default, fast**
- `sentence-transformers/all-mpnet-base-v2` (768 dims) - Better quality
- `BAAI/bge-small-en-v1.5` (384 dims) - Good balance
- `BAAI/bge-base-en-v1.5` (768 dims) - Strong performance
- `BAAI/bge-large-en-v1.5` (1024 dims) - Best quality, slower

**Important**: If you change models, you must:
1. Update the `VECTOR(dimension)` in SQL setup files
2. Re-run the setup scripts
3. Re-generate all embeddings

## 🎯 How Vector Search Works

### 1. Encoding
When you search, your query is converted to a vector:
```python
model = SentenceTransformer("all-MiniLM-L6-v2")
query_embedding = model.encode("AI developments")
# Returns: [0.023, -0.145, 0.678, ...] (384 dimensions)
```

### 2. Similarity Calculation
pgvector compares your query vector to stored embeddings using **cosine similarity**:

```
similarity = 1 - (query_embedding <=> stored_embedding)
```

The `<=>` operator is cosine distance (0 = identical, 2 = opposite).
We subtract from 1 to get similarity (1 = identical, 0 = unrelated).

### 3. Indexing
The HNSW (Hierarchical Navigable Small World) index enables fast approximate nearest neighbor search:
- **Without index**: O(n) - checks every vector
- **With HNSW**: O(log n) - uses graph structure for fast lookup

### 4. Result Ranking
Results are sorted by similarity score, highest first.

## 📊 Performance

### Query Speed
- **First search**: 2-5 seconds (model loading)
- **Subsequent searches**: 100-500ms
- **With HNSW index**: ~50-200ms for 100k+ vectors

### Optimization Tips

1. **Ensure HNSW indexes exist**:
```sql
-- Check indexes
SELECT indexname, tablename 
FROM pg_indexes 
WHERE tablename LIKE '%embeddings';
```

2. **Reduce search limit**: Lower values = faster
3. **Filter by ticker**: Reduces search space
4. **Use smaller model**: all-MiniLM-L6-v2 is fastest

## 🐛 Troubleshooting

### "No results found"
**Cause**: Embeddings tables are empty
**Fix**: Run `notebooks/ingest_ticker_news_embeddings`

### "Model loading failed"
**Cause**: sentence-transformers not installed
**Fix**: `pip install sentence-transformers torch`

### "Table does not exist"
**Cause**: SQL setup scripts not run
**Fix**: Run sql/02_setup_embeddings_table.sql and sql/03_setup_chunk_embeddings_table.sql

### "Extension 'vector' not found"
**Cause**: pgvector extension not enabled
**Fix**: Run `CREATE EXTENSION IF NOT EXISTS vector;` in Lakebase

### Slow searches (> 1 second)
**Cause**: Missing HNSW index
**Fix**: 
```sql
CREATE INDEX IF NOT EXISTS idx_ticker_news_embeddings_embedding
ON ticker_news_embeddings
USING hnsw (embedding vector_cosine_ops);
```

### "Dimension mismatch" error
**Cause**: Model dimension doesn't match table VECTOR() size
**Fix**: 
1. Check model dimensions
2. Update table definition
3. Re-create table and re-generate embeddings

## 🎓 Example Search Queries

Try these natural language queries:

**Market trends**:
- "Latest earnings reports"
- "Stock price movements this week"
- "Market volatility news"

**Company-specific**:
- "Apple product announcements"
- "Microsoft cloud computing"
- "Tesla production updates"

**Technology**:
- "AI and machine learning developments"
- "Semiconductor industry news"
- "5G technology updates"

**Sentiment**:
- "Positive news about tech stocks"
- "Bearish sentiment on energy sector"
- "Analyst upgrades"

## 🔮 Future Enhancements

Potential improvements:
- **Hybrid search**: Combine keyword + semantic search
- **Date filtering**: "News from last week"
- **Multi-ticker**: "Compare AAPL and MSFT"
- **Question answering**: Extract specific facts
- **Chat interface**: Conversational search
- **Reranking**: Use cross-encoder for better results
- **Highlights**: Show matching passages in documents
- **Saved searches**: Store frequent queries
- **Alerts**: Notify on new relevant articles

## 📚 References

- [pgvector documentation](https://github.com/pgvector/pgvector)
- [sentence-transformers docs](https://www.sbert.net/)
- [HNSW algorithm](https://arxiv.org/abs/1603.09320)
- [Cosine similarity](https://en.wikipedia.org/wiki/Cosine_similarity)
