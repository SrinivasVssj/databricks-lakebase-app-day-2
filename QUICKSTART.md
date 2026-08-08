# 🚀 Vector Search Quick Start Guide

Get your semantic search feature running in minutes!

## ✅ Prerequisites Checklist

- [ ] Lakebase Postgres database is set up
- [ ] Python 3.9+ installed
- [ ] Git repository cloned
- [ ] Databricks workspace access

## 📋 Step-by-Step Setup

### Step 1: Install Dependencies (2 min)

```bash
cd databricks-lakebase-app-day-2
pip install -r requirements.txt
```

This installs:
- Flask (web framework)
- sentence-transformers (embeddings)
- psycopg2 (PostgreSQL driver)
- databricks-sdk
- And more...

### Step 2: Setup Database Tables (5 min)

Run these SQL scripts in your Lakebase database:

```bash
# 1. Enable pgvector extension
# Run this in Lakebase SQL console:
CREATE EXTENSION IF NOT EXISTS vector;

# 2. Create tables
# Run each script in order:
sql/01_setup_news_table.sql
sql/02_setup_embeddings_table.sql
sql/03_setup_chunk_embeddings_table.sql
```

**Important**: Replace `{{EMBEDDING_DIM}}` with `384` in the SQL files before running (for the default all-MiniLM-L6-v2 model).

### Step 3: Add Data (10 min)

#### Option A: Via Web UI
1. Start the Flask app: `python app.py`
2. Visit http://localhost:8000
3. Add a ticker to your watchlist (e.g., "AAPL")
4. It will automatically fetch the latest price

#### Option B: Via API
```bash
# Add ticker to watchlist
curl -X POST http://localhost:8000/watchlist \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'

# Sync news for that ticker
curl -X POST http://localhost:8000/news/sync \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL", "MSFT", "GOOGL"], "limit": 50}'
```

### Step 4: Generate Embeddings (5-10 min)

Open and run the notebook:
```
notebooks/ingest_ticker_news_embeddings
```

This notebook will:
1. Read your watchlist
2. Fetch news articles (if not already synced)
3. Generate document embeddings
4. Split articles into chunks
5. Generate chunk embeddings
6. Store everything in Lakebase

**Note**: First run may take longer as it downloads the embedding model (~90MB).

### Step 5: Search! (< 1 min)

You're ready! Try searching:

#### Via Web UI
1. Visit http://localhost:8000
2. Type a query like "AI developments in tech"
3. Click "Search"
4. See results ranked by relevance!

#### Via API
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What news is there about AI?",
    "limit": 5
  }'
```

#### Via Test Script
```bash
python test_search.py "AI developments"
python test_search.py "earnings news" --ticker AAPL
python test_search.py --stats
```

## 🎯 What You Can Do Now

### Search Examples

Try these queries:

**Market trends**:
- "Latest earnings reports"
- "Stock price movements"
- "Market volatility"

**Technology**:
- "AI and machine learning news"
- "Cloud computing updates"
- "Semiconductor industry"

**Company-specific**:
- "Apple product launches"
- "Microsoft AI features"
- "Tesla production"

**With ticker filter**:
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "quarterly earnings",
    "ticker": "AAPL",
    "limit": 10
  }'
```

### Check Statistics

```bash
# Via API
curl http://localhost:8000/search/stats

# Via test script
python test_search.py --stats
```

Shows:
- Total documents and chunks indexed
- Available tickers
- Date range of news
- Embedding model used

## 📊 Understanding Results

### Document Results
Each document shows:
- **Title**: Article headline
- **Similarity**: 0-100% (higher = more relevant)
- **Ticker**: Stock symbol
- **Date**: Publication date
- **Sentiment**: positive/negative/neutral
- **Description**: Article summary
- **Link**: URL to full article

### Chunk Results
Each chunk shows:
- **Chunk #**: Paragraph number in article
- **Similarity**: 0-100%
- **Ticker**: Stock symbol
- **Text**: The actual passage
- **Source**: Original article info
- **Link**: URL to full article

## 🔧 Troubleshooting

### "No results found"
**Problem**: Embeddings tables are empty  
**Solution**: Run the notebook `notebooks/ingest_ticker_news_embeddings`

### "Table does not exist"
**Problem**: SQL setup scripts not run  
**Solution**: Run all SQL scripts in `sql/` directory

### "Module not found: sentence_transformers"
**Problem**: Dependencies not installed  
**Solution**: `pip install -r requirements.txt`

### "Connection refused" 
**Problem**: Flask app not running  
**Solution**: `python app.py`

### First search is slow (5+ seconds)
**Expected**: Model loading on first request  
**Note**: Subsequent searches will be fast (~200ms)

### "Extension 'vector' not found"
**Problem**: pgvector not enabled  
**Solution**: Run `CREATE EXTENSION IF NOT EXISTS vector;` in Lakebase

## 🎓 Next Steps

### Customize the Model

Want better embeddings? Change the model:

1. Update environment:
```bash
export EMBEDDING_MODEL="sentence-transformers/all-mpnet-base-v2"
```

2. Update SQL (change VECTOR dimension):
```sql
-- For all-mpnet-base-v2 (768 dims)
VECTOR(768) instead of VECTOR(384)
```

3. Re-run setup scripts

4. Re-generate embeddings (run notebook)

### Add More Tickers

```bash
# Add to watchlist
curl -X POST http://localhost:8000/watchlist \
  -H "Content-Type: application/json" \
  -d '{"symbol": "TSLA"}'

# Sync news
curl -X POST http://localhost:8000/news/sync \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["TSLA"], "limit": 50}'

# Re-run notebook to generate embeddings
```

### Schedule Automatic Updates

Set up a Databricks Job to:
1. Run daily at 9 AM
2. Execute the `ingest_ticker_news_embeddings` notebook
3. Keeps your search index fresh with latest news

## 📚 Learn More

- **Full documentation**: See `SEARCH_FEATURE_README.md`
- **Architecture**: See `ARCHITECTURE.md`
- **API details**: See `SEARCH_FEATURE_README.md` → "Search Endpoints"
- **Lakebase tables**: See `SEARCH_FEATURE_README.md` → "Lakebase Tables"

## 💡 Tips

1. **Start small**: Begin with 2-3 tickers, 50 articles each
2. **Test often**: Use `test_search.py --stats` to verify data
3. **Monitor logs**: Watch Flask output for errors
4. **Optimize later**: HNSW indexes automatically speed up large datasets
5. **Keep model in memory**: Don't restart Flask unnecessarily

## 🎉 Success Criteria

You know it's working when:
- ✅ Search returns results with similarity scores
- ✅ Results are relevant to your query
- ✅ Both documents and chunks appear
- ✅ Sentiment badges show up
- ✅ Search completes in < 1 second (after first)

Happy searching! 🚀
