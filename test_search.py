#!/usr/bin/env python3
"""
Test script for the vector search API.

Usage:
    python test_search.py "your search query"
    python test_search.py "AI developments" --ticker MSFT
    python test_search.py "earnings news" --limit 20
"""

import argparse
import json
import requests


def test_search(base_url, prompt, ticker=None, limit=10):
    """Test the /search endpoint."""
    url = f"{base_url}/search"
    
    payload = {
        "prompt": prompt,
        "limit": limit
    }
    
    if ticker:
        payload["ticker"] = ticker.upper()
    
    print(f"\n🔍 Searching for: '{prompt}'")
    if ticker:
        print(f"   Filtered by ticker: {ticker}")
    print(f"   Limit: {limit}")
    print("-" * 60)
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Print summary
        print(f"\n📊 Results Summary:")
        print(f"   Model: {data.get('model', 'unknown')}")
        print(f"   Documents found: {data['results_count']['documents']}")
        print(f"   Chunks found: {data['results_count']['chunks']}")
        
        # Print top documents
        print(f"\n📄 Top Documents:")
        if data['documents']:
            for i, doc in enumerate(data['documents'][:3], 1):
                score = doc.get('similarity_score', 0) * 100
                title = doc.get('title', 'No title')
                ticker_sym = doc.get('ticker', 'N/A')
                sentiment = doc.get('sentiment', 'neutral')
                
                print(f"\n  {i}. [{ticker_sym}] {title}")
                print(f"     Similarity: {score:.1f}%")
                print(f"     Sentiment: {sentiment}")
                if doc.get('description'):
                    desc = doc['description'][:100] + "..." if len(doc.get('description', '')) > 100 else doc.get('description', '')
                    print(f"     {desc}")
        else:
            print("   No documents found.")
        
        # Print top chunks
        print(f"\n📝 Top Chunks:")
        if data['chunks']:
            for i, chunk in enumerate(data['chunks'][:3], 1):
                score = chunk.get('similarity_score', 0) * 100
                text = chunk.get('chunk_text', '')[:150] + "..." if len(chunk.get('chunk_text', '')) > 150 else chunk.get('chunk_text', '')
                ticker_sym = chunk.get('ticker', 'N/A')
                
                print(f"\n  {i}. [{ticker_sym}] Chunk #{chunk.get('chunk_index', 0) + 1}")
                print(f"     Similarity: {score:.1f}%")
                print(f"     {text}")
        else:
            print("   No chunks found.")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error: {e}")
        return None
    except json.JSONDecodeError:
        print(f"\n❌ Invalid JSON response")
        return None


def test_stats(base_url):
    """Test the /search/stats endpoint."""
    url = f"{base_url}/search/stats"
    
    print(f"\n📈 Fetching search statistics...")
    print("-" * 60)
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"\n📊 Database Statistics:")
        print(f"   Total documents: {data.get('total_documents', 0):,}")
        print(f"   Total chunks: {data.get('total_chunks', 0):,}")
        print(f"   Model: {data.get('model', 'unknown')}")
        
        if data.get('tickers'):
            print(f"\n📌 Available tickers:")
            for ticker_info in data['tickers']:
                ticker = ticker_info.get('ticker', 'N/A')
                count = ticker_info.get('doc_count', 0)
                print(f"   • {ticker}: {count} documents")
        
        if data.get('date_range'):
            date_range = data['date_range']
            print(f"\n📅 Date range:")
            print(f"   Earliest: {date_range.get('earliest', 'N/A')}")
            print(f"   Latest: {date_range.get('latest', 'N/A')}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Test the vector search API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "AI developments"
  %(prog)s "earnings news" --ticker AAPL
  %(prog)s "market volatility" --limit 20
  %(prog)s --stats
        """
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        help="Search query (natural language)"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--ticker",
        help="Filter by ticker symbol (e.g., AAPL, MSFT)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results (default: 10, max: 100)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics instead of searching"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response"
    )
    
    args = parser.parse_args()
    
    if args.stats:
        data = test_stats(args.base_url)
        if args.json and data:
            print(f"\n{json.dumps(data, indent=2)}")
    elif args.query:
        data = test_search(
            args.base_url,
            args.query,
            ticker=args.ticker,
            limit=args.limit
        )
        if args.json and data:
            print(f"\n{json.dumps(data, indent=2)}")
    else:
        parser.print_help()
        print("\n💡 Tip: Run with --stats to see available data first")


if __name__ == "__main__":
    main()
