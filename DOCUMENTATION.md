# Databricks Lakebase News Search Application - Technical Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Technical Architecture](#technical-architecture)
3. [Functional Features](#functional-features)
4. [Design Decisions](#design-decisions)
5. [Data Schema](#data-schema)
6. [API Reference](#api-reference)
7. [User Workflow](#user-workflow)
8. [Implementation Details](#implementation-details)

---

## Project Overview

The **Databricks Lakebase News Search Application** is a semantic search system built on Databricks' Lakebase Postgres with pgvector extension. It enables natural language search over financial news articles using vector embeddings, providing intelligent document discovery with automatic summarization.

### Core Purpose
Transform unstructured news content into searchable knowledge by:
- Converting news articles to vector embeddings using sentence transformers
- Storing embeddings in Lakebase Postgres with pgvector for efficient similarity search
- Providing a web interface for semantic search with natural language queries
- Generating intelligent summaries from search results

### Technology Stack
- **Database**: Lakebase Postgres with pgvector extension
- **Backend**: Flask (Python)
- **Frontend**: HTML/CSS/JavaScript
- **ML Models**: sentence-transformers/all-MiniLM-L6-v2 (384-dimensional embeddings)
- **Deployment**: Databricks Apps V2

---

## Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface (HTML)                    │
│  • Search form with prompt + limit + ticker filter          │
│  • Dynamic summary generation                                │
│  • Document results rendering                                │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/JSON
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Flask Backend (app.py)                     │
│  • /search endpoint: semantic search orchestration          │
│  • Embedding generation (sentence-transformers)             │
│  • SQL query construction with pgvector operators           │
└──────────────────────┬──────────────────────────────────────┘
                       │ PostgreSQL Protocol
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Lakebase Postgres + pgvector                    │
│  • ticker_news_embeddings table (documents)                 │
│  • Vector similarity search (<=> operator)                  │
│  • Indexed vector columns for performance                   │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Ingestion Phase** (handled by separate notebook):
   - Raw news data → Lakebase `ticker_news` table
   - Batch embedding generation using sentence-transformers
   - Embeddings stored in `ticker_news_embeddings` table with pgvector type

2. **Search Phase** (runtime):
   - User submits natural language query
   - Backend generates query embedding (384-dim vector)
   - pgvector performs cosine similarity search using `<=>` operator
   - Results ranked by similarity score, limited to top k
   - Frontend generates summary and renders documents

### Database Connection

**Connection String Format**:
```
postgresql://{user}:{token}@{host}/{database}
```

**Key Design Points**:
- Uses Databricks OAuth token for authentication (dynamic retrieval)
- Connection pooling disabled (`poolclass=NullPool`) for serverless compatibility
- SSL mode set to `require` for secure communication
- Database/host/project/branch read from environment variables

---

## Functional Features

### 1. Semantic Search
**What it does**: Finds news articles semantically similar to user's natural language query, not just keyword matching.

**Example**:
- Query: "company expanding into renewable energy"
- Matches: Articles about solar investments, green initiatives, sustainability pivots
- Does NOT require exact phrase "renewable energy" to appear

**Parameters**:
- `prompt`: Natural language search query (required)
- `limit`: Number of results to return (user-specified, default 5)
- `ticker`: Optional stock ticker filter (e.g., "AAPL", "TSLA")

### 2. Intelligent Document Ranking
**Similarity scoring**: Uses cosine similarity (0-1 scale) to rank documents
- Higher scores = more semantically relevant
- Results sorted by descending similarity
- Score displayed as percentage in UI

### 3. Automatic Summarization
**Pre-result summary**: Before showing individual documents, generates a contextual summary covering:
- Unique tickers mentioned across results
- Sentiment distribution (positive/negative/neutral)
- Key headlines and highlights
- Direct answer to user's query based on retrieved metadata

**Technical approach**: Client-side JavaScript aggregation of document metadata (no LLM required)

### 4. Ticker Filtering
**Optional constraint**: Narrow search to specific stock ticker
- Applied at database query level (WHERE clause)
- Reduces result space for focused research

### 5. Dynamic Result Limits
**User-controlled**: Specify how many documents to retrieve (1-50)
- UI displays availability messaging if fewer documents exist
- Example: Request 20, get 8 → "That's all we have - 8 relevant documents available"

---

## Design Decisions

### 1. Document-Only Search (No Chunk Search)
**Decision**: Removed chunk-based search, focusing solely on document-level embeddings.

**Rationale**:
- **Simplicity**: Document embeddings capture article-level semantic meaning, sufficient for news discovery
- **Performance**: Single query vs. dual document+chunk queries reduces latency
- **Bug elimination**: Chunk rendering had persistent JavaScript errors (`chunksResults is not defined`)
- **User clarity**: Document results are more intuitive than mixing documents and chunks

**Trade-off**: Less granular passage-level search, but improved reliability and UX

### 2. Client-Side Summarization
**Decision**: Generate summaries in browser JavaScript using document metadata.

**Rationale**:
- **Cost**: No LLM API calls required
- **Speed**: Instant summary generation (no network latency)
- **Transparency**: Summary logic is deterministic and inspectable
- **Privacy**: No data sent to external services

**Trade-off**: Summaries are template-based rather than free-form natural language

### 3. Serverless Architecture (NullPool)
**Decision**: Disable connection pooling (`poolclass=NullPool`).

**Rationale**:
- **Databricks Apps V2 context**: Serverless environment with ephemeral connections
- **Token refresh**: OAuth tokens expire; each request retrieves fresh token
- **Concurrency**: Avoids stale connection issues in multi-user scenarios

**Trade-off**: Slight overhead per request, but necessary for correctness

### 4. Single Embedding Model
**Decision**: Use `sentence-transformers/all-MiniLM-L6-v2` for both ingestion and search.

**Rationale**:
- **Consistency**: Query and document embeddings must use identical model for valid similarity
- **Balance**: 384-dim vectors balance expressiveness and storage/speed
- **Proven**: Well-established model for semantic search tasks

**Trade-off**: Not state-of-art for all domains, but sufficient for news articles

### 5. Cosine Similarity Metric
**Decision**: Use `<=>` pgvector operator (cosine distance).

**Rationale**:
- **Normalization-aware**: Accounts for vector magnitude differences
- **Semantic search standard**: Industry norm for sentence embeddings
- **pgvector native**: Efficient indexed operation

**Formula**: `1 - cosine_distance = similarity_score`

### 6. No Hybrid Search
**Decision**: Pure semantic search; no keyword/BM25 hybrid.

**Rationale**:
- **Simplicity**: Single ranking mechanism easier to tune and explain
- **News domain**: Semantic search particularly effective for news (varied phrasing, synonyms)
- **Infrastructure**: Avoids full-text search index complexity

**Trade-off**: May miss exact technical term matches, but gains conceptual understanding

---

## Data Schema

### ticker_news_embeddings (Primary Search Table)

```sql
CREATE TABLE ticker_news_embeddings (
    id TEXT PRIMARY KEY,
    ticker TEXT,
    title TEXT,
    author TEXT,
    published_utc TIMESTAMP,
    article_url TEXT,
    description TEXT,
    publisher_name TEXT,
    sentiment TEXT,
    embedding vector(384),  -- pgvector type
    -- Metadata columns for additional context
);

CREATE INDEX ON ticker_news_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- Performance optimization
```

**Column Descriptions**:
- `id`: Unique article identifier
- `ticker`: Stock ticker symbol (e.g., "AAPL", "MSFT")
- `title`: Article headline
- `author`: Article author name
- `published_utc`: Publication timestamp
- `article_url`: Link to original article
- `description`: Article summary/snippet
- `publisher_name`: News source (e.g., "Bloomberg", "Reuters")
- `sentiment`: Sentiment classification (positive/negative/neutral)
- `embedding`: 384-dimensional vector representation

### ticker_news_chunk_embeddings (Deprecated)
**Status**: Table exists but not used in current application.

**Original purpose**: Store chunk-level embeddings for passage-level search.

**Why deprecated**: See Design Decision #1.

---

## API Reference

### GET /
**Description**: Serve main application page.

**Response**: HTML page with search interface.

---

### POST /search
**Description**: Semantic search endpoint.

**Request Body** (JSON):
```json
{
  "prompt": "companies investing in AI infrastructure",
  "limit": 10,
  "ticker": "NVDA"  // optional
}
```

**Response** (JSON):
```json
{
  "documents": [
    {
      "id": "abc123",
      "ticker": "NVDA",
      "title": "NVIDIA Expands Data Center AI Capabilities",
      "description": "Company announces new infrastructure investments...",
      "author": "Jane Smith",
      "published_utc": "2024-01-15T10:30:00",
      "article_url": "https://example.com/article",
      "publisher_name": "TechNews",
      "sentiment": "positive",
      "similarity_score": 0.8234
    }
    // ... more documents
  ],
  "results_count": {
    "documents": 10
  },
  "ticker_filter": "NVDA",
  "model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

**Error Response**:
```json
{
  "error": "Failed to generate embedding: [error details]"
}
```

**HTTP Status Codes**:
- `200`: Success
- `400`: Invalid request (missing prompt)
- `500`: Server error (database connection, embedding generation)

---

## User Workflow

### Standard Search Flow

1. **User enters search query**:
   - Types natural language prompt (e.g., "tech companies facing regulatory challenges")
   - Specifies desired number of results (1-50)
   - Optionally filters by ticker

2. **Submit search**:
   - Click "Search" button
   - Frontend sends POST request to `/search` endpoint
   - Loading indicator displayed

3. **Backend processing**:
   - Extract prompt, limit, ticker from request
   - Generate 384-dim embedding for prompt
   - Query Lakebase Postgres with pgvector similarity
   - Apply ticker filter if specified
   - Limit results to top k by similarity

4. **Results rendering**:
   - **Summary section**: Aggregated insights from all retrieved documents
     - Tickers mentioned
     - Sentiment distribution
     - Key headlines
     - Quick answer to query
   - **Individual documents**: Each result card shows:
     - Title (clickable link to original article)
     - Similarity score (percentage)
     - Ticker, date, publisher, author
     - Sentiment badge (color-coded)
     - Description snippet

5. **Result interpretation**:
   - Higher percentage = more relevant to query
   - Green badges = positive sentiment, red = negative, gray = neutral
   - "That's all we have" message if fewer results than requested

### Example Use Cases

**Investment Research**:
- Query: "merger and acquisition activity in semiconductor industry"
- Ticker filter: Leave blank (search all tickers)
- Limit: 20
- Result: Top 20 M&A news articles across all semiconductor companies

**Company Monitoring**:
- Query: "earnings guidance and forecast changes"
- Ticker filter: "TSLA"
- Limit: 10
- Result: Top 10 Tesla articles about earnings forecasts

**Thematic Analysis**:
- Query: "supply chain disruptions and inventory issues"
- Ticker filter: Leave blank
- Limit: 50
- Result: Broad view of supply chain news across all companies

---

## Implementation Details

### Backend (app.py)

#### Embedding Generation
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
embedding = model.encode(prompt)  # Returns 384-dim numpy array
embedding_list = embedding.tolist()  # Convert for SQL parameter
```

**Key points**:
- Model loaded once at startup (cached)
- Encoding takes ~50-200ms depending on prompt length
- Output normalized by default

#### SQL Query Construction

**Without ticker filter**:
```sql
SELECT 
    id, ticker, title, description, author, 
    published_utc, article_url, publisher_name, sentiment,
    1 - (embedding <=> %s::vector) AS similarity_score
FROM ticker_news_embeddings
ORDER BY embedding <=> %s::vector
LIMIT %s
```

**With ticker filter**:
```sql
SELECT ... 
FROM ticker_news_embeddings
WHERE ticker = %s
ORDER BY embedding <=> %s::vector
LIMIT %s
```

**Parameter ordering bug fix**:
- Original: `(embedding, ticker, limit)` → caused "invalid input syntax" when ticker used
- Fixed: `(embedding, embedding, limit)` or `(embedding, ticker, embedding, limit)`
- Root cause: pgvector requires embedding parameter for both SELECT and ORDER BY

#### Database Connection Management
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
token = w.dbutils.secrets.get(scope="...", key="databricks-token")

engine = create_engine(
    f"postgresql://{user}:{token}@{host}/{database}",
    connect_args={"sslmode": "require"},
    poolclass=NullPool  # Disable pooling for serverless
)
```

**Token refresh**: New connection created per request, fetching current token.

### Frontend (index.html)

#### Summary Generation Logic
```javascript
function generateSummary(prompt, documents) {
    // Extract unique tickers
    const tickers = [...new Set(documents.map(d => d.ticker))];
    
    // Count sentiments
    const sentiments = documents.reduce((acc, d) => {
        if (d.sentiment) acc[d.sentiment] = (acc[d.sentiment] || 0) + 1;
        return acc;
    }, {});
    
    // Extract headlines (top 3)
    const headlines = documents.slice(0, 3).map(d => d.title);
    
    // Build summary HTML
    return `
        <strong>Quick Answer:</strong> Based on your query "${prompt}", 
        we found ${documents.length} relevant articles...
        [ticker list, sentiment breakdown, headlines]
    `;
}
```

**Approach**: Pure metadata aggregation, no NLP or LLM.

#### Dynamic UI Updates
```javascript
// Availability messaging
if (docCount < limit && docCount > 0) {
    availabilityMsg = `(That's all we have - ${docCount} relevant documents available)`;
} else if (docCount === 0) {
    availabilityMsg = `(No documents found)`;
}

// Update header
documentsHeader.textContent = `📄 Top ${limit} Documents`;
```

**User experience**: Clear feedback about result availability.

#### Result Card Rendering
```javascript
documents.forEach((doc) => {
    const score = (doc.similarity_score * 100).toFixed(1);  // 0-100%
    const sentiment = getSentimentClass(doc.sentiment);  // CSS class
    
    // Build card HTML with title, meta, description, link
    div.innerHTML = `...`;
    documentsResults.appendChild(div);
});
```

**Sentiment styling**:
- Positive: Green badge
- Negative: Red badge
- Neutral: Gray badge

---

## Performance Considerations

### Database Query Performance
- **Index**: ivfflat index on embedding column (lists=100)
- **Typical latency**: 50-200ms for top-k search (k≤50)
- **Scalability**: Sublinear with dataset size due to approximate search

### Embedding Generation
- **Model size**: ~80MB (loaded in memory)
- **Inference time**: ~50-200ms per query
- **Batch optimization**: Not applicable (single query per request)

### End-to-End Latency
- **Typical request**: 200-500ms
- **Breakdown**:
  - Embedding generation: 100ms
  - Database query: 100ms
  - Network + rendering: 100ms

---

## Future Enhancement Opportunities

### Short-Term
1. **Advanced filtering**: Date range, publisher, sentiment
2. **Result explanations**: Highlight matching semantic concepts
3. **Search history**: Save and revisit past queries

### Medium-Term
1. **Hybrid search**: Combine semantic + keyword (BM25)
2. **Query expansion**: Automatic synonym/related term injection
3. **Result clustering**: Group similar articles

### Long-Term
1. **Multi-modal search**: Images, video transcripts
2. **Personalization**: User-specific ranking
3. **Real-time updates**: Streaming ingestion of new articles

---

## Troubleshooting

### Common Issues

**1. "chunksResults is not defined" error**
- **Cause**: Legacy chunk rendering code still present
- **Fix**: All chunk-related JavaScript removed in latest version

**2. "Invalid input syntax for type vector"**
- **Cause**: SQL parameter ordering mismatch
- **Fix**: Ensure embedding parameter passed twice (SELECT + ORDER BY)

**3. "No documents found"**
- **Causes**:
  - Embeddings not generated (run ingestion notebook)
  - Query too specific/narrow
  - Ticker filter excluding all results
- **Fix**: Verify data exists, broaden query, remove ticker filter

**4. Slow query performance**
- **Causes**:
  - Missing ivfflat index
  - Very large result limit (k>100)
- **Fix**: Create index, reduce limit to 20-50

---

## Deployment

### Databricks Apps V2
1. Define `app.yaml` with compute resources
2. Deploy via `databricks apps deploy`
3. App receives dedicated URL: `https://<workspace-host>/apps/<app-name>`

### Environment Variables
Required in `databricks.yml` or app config:
- `LAKEBASE_HOST`: Postgres endpoint hostname
- `LAKEBASE_DATABASE`: Database name
- `LAKEBASE_PROJECT`: Project name
- `LAKEBASE_BRANCH`: Branch name

### Dependencies
- Flask
- SQLAlchemy
- psycopg2-binary
- sentence-transformers
- torch
- databricks-sdk

---

## Conclusion

This application demonstrates a production-ready semantic search system leveraging Databricks Lakebase Postgres with pgvector. By focusing on document-level search with intelligent summarization, it provides a clean, performant user experience for financial news discovery. The design prioritizes simplicity, reliability, and cost-efficiency while maintaining semantic search quality.