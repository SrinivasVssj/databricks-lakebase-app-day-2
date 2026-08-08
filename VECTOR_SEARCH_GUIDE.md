# Vector Search Feature

## Overview

The application now includes semantic search capabilities that allow you to find relevant news documents and chunks using natural language queries. The search uses vector embeddings and cosine similarity to find the most relevant content.

## How It Works

1. **User enters a search prompt** - You type a natural language question or topic (e.g., "What news is there about AI and technology?")

2. **Embedding generation** - The app generates a vector embedding for your prompt using the same model that was used to embed the news articles (by default: `sentence-transformers/all-MiniLM-L6-v2`)

3. **Vector similarity search** - The app queries two tables in Lakebase:
   - `ticker_news_embeddings` - Document-level embeddings (entire articles)
   - `ticker_news_chunk_embeddings` - Chunk-level embeddings (article sections/paragraphs)

4. **Results ranked by similarity** - Results are ordered by cosine similarity score (0-100% match)

## API Endpoint

### `POST /search`

**Request body:**
```json
{
  "prompt": "What news is there about AI?",
  "limit": 10
}
```

**Response:**
```json
{
  "prompt": "What news is there about AI?",
  "model": "sentence-transformers/all-MiniLM-L6-v2",
  "documents": [
    {
      "id": "article_123",
      "ticker": "MSFT",
      "title": "Microsoft announces new AI features",
      "published_utc": "2026-08-07T10:00:00Z",
      "similarity_score": 0.87
    }
  ],
  "chunks": [
    {
      "id": "chunk_456",
      "article_id": "article_123",
      "ticker": "MSFT",
      "chunk_index": 2,
      "chunk_text": "The company unveiled several AI-powered tools...",
      "similarity_score": 0.91
    }
  ]
}
```

## UI Usage

1. Navigate to the app's home page
2. Look for the **"🔍 Semantic News Search"** section at the top
3. Enter your search query in natural language
4. Click **"Search"**
5. View results in two sections:
   - **📄 Top Documents** - Full articles ranked by relevance
   - **📝 Top Chunks** - Specific passages/paragraphs from articles

## Setup Requirements

### 1. Install Dependencies

The `requirements.txt` has been updated to include:
```
sentence-transformers>=2.2.0
torch>=2.0.0
```

Install with:
```bash
pip install -r requirements.txt
```

### 2. Ensure Embeddings Tables Exist

Before using the search feature, make sure you've:

1. Run `sql/02_setup_embeddings_table.sql` to create `ticker_news_embeddings`
2. Run `sql/03_setup_chunk_embeddings_table.sql` to create `ticker_news_chunk_embeddings`
3. Run the `notebooks/ingest_ticker_news_embeddings` notebook to populate these tables

### 3. Configure Environment Variables (Optional)

You can customize the following in your environment:

```bash
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"  # Default
EMBEDDINGS_TABLE_NAME="ticker_news_embeddings"  # Default
CHUNK_EMBEDDINGS_TABLE_NAME="ticker_news_chunk_embeddings"  # Default
```

## Performance Notes

- **First search is slower** - The embedding model is loaded lazily on first use
- **Subsequent searches are fast** - The model stays in memory
- **pgvector HNSW index** - Provides fast approximate nearest neighbor search
- **Cosine similarity** - Used for measuring vector similarity (range: 0-1)

## Example Search Queries

- "Latest AI developments"
- "Tech companies stock performance"
- "News about Microsoft and Google"
- "Earnings reports"
- "Market sentiment on electric vehicles"

## Troubleshooting

### No results found
- Ensure the embeddings tables are populated (run the notebook)
- Check that you have news data synced via `/news/sync` endpoint
- Verify your watchlist has tickers (the notebook fetches news for watchlisted tickers)

### Search endpoint returns 500 error
- Check that the embedding model can be loaded
- Verify pgvector extension is enabled in Lakebase
- Check application logs for detailed error messages

### Slow performance
- Ensure HNSW indexes exist on the embedding columns
- Consider using a smaller/faster embedding model
- Reduce the `limit` parameter in search requests

## Architecture

```
User Query
    |
    v
SentenceTransformer (encode)
    |
    v
Query Embedding Vector
    |
    v
Lakebase Postgres (pgvector)
    |
    +-- ticker_news_embeddings (document-level)
    |
    +-- ticker_news_chunk_embeddings (chunk-level)
    |
    v
Cosine Similarity Search
    |
    v
Ranked Results (JSON)
    |
    v
UI Rendering
```

## Future Enhancements

- Filter by ticker symbol
- Filter by date range
- Hybrid search (keyword + semantic)
- Reranking with cross-encoder
- Question answering over retrieved chunks
- Chat interface with context
