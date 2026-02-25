"""
Script to manually refresh the full S&P 500 universe.
Run this from the backend directory with the virtual environment activated.

Usage:
    python scripts/refresh_sp500.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.services.ingestion import refresh_prices_and_fundamentals
from app.services.universe import get_universe


def main():
    print("=" * 80)
    print("S&P 500 Full Refresh")
    print("=" * 80)
    
    # Fetch S&P 500 tickers
    print("\n1. Fetching S&P 500 ticker list from Wikipedia...")
    tickers = get_universe(use_full_sp500=True)
    print(f"   Found {len(tickers)} tickers")
    
    # Confirm with user
    print(f"\n2. About to refresh {len(tickers)} tickers with 2 years of data")
    print("   This will take approximately 10-15 minutes")
    print("   Batch size: 50 tickers per batch")
    print("   Rate limit delay: 1 second between batches")
    
    confirm = input("\n   Continue? (yes/no): ").strip().lower()
    if confirm not in ["yes", "y"]:
        print("   Cancelled.")
        return
    
    # Execute refresh
    print("\n3. Starting refresh...")
    db = SessionLocal()
    try:
        stats = refresh_prices_and_fundamentals(
            db=db,
            tickers=tickers,
            period="2y",
            batch_size=50,
            delay_seconds=1.0,
        )
        
        print("\n" + "=" * 80)
        print("Refresh Complete!")
        print("=" * 80)
        print(f"Tickers processed:    {stats['tickers']}")
        print(f"Batches processed:    {stats['batches_processed']}")
        print(f"Price rows inserted:  {stats['price_rows']:,}")
        print(f"Fundamental rows:     {stats['fundamental_rows']:,}")
        print(f"Indicator rows:       {stats['indicator_rows']:,}")
        print(f"Duration:             {stats['duration_seconds']:.1f} seconds")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error during refresh: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
