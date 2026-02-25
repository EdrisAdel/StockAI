import logging
from functools import lru_cache

import pandas as pd

logger = logging.getLogger(__name__)

SP500_SAMPLE = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "GOOGL",
    "TSLA",
    "BRK-B",
    "JPM",
    "XOM",
]

SECTOR_FALLBACK = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "NVDA": "Technology",
    "AMZN": "Consumer Discretionary",
    "META": "Communication Services",
    "GOOGL": "Communication Services",
    "TSLA": "Consumer Discretionary",
    "BRK-B": "Financials",
    "JPM": "Financials",
    "XOM": "Energy",
}


@lru_cache(maxsize=1)
def fetch_sp500_tickers() -> list[str]:
    """
    Fetch current S&P 500 ticker list from Wikipedia.
    Cached to avoid repeated requests.
    
    Returns:
        List of ticker symbols (e.g., ['AAPL', 'MSFT', ...])
    """
    try:
        logger.info("Fetching S&P 500 tickers from Wikipedia...")
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        
        # Set User-Agent header to avoid 403 errors
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        tables = pd.read_html(url, storage_options=headers)
        
        # First table contains the current S&P 500 constituents
        df = tables[0]
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        
        logger.info(f"Successfully fetched {len(tickers)} S&P 500 tickers")
        return tickers
    except Exception as e:
        logger.error(f"Failed to fetch S&P 500 tickers from Wikipedia: {e}")
        logger.warning("Falling back to sample universe")
        return SP500_SAMPLE


def get_universe(use_full_sp500: bool = False) -> list[str]:
    """
    Get the stock universe to use for analysis.
    
    Args:
        use_full_sp500: If True, fetch full S&P 500. If False, use sample set.
    
    Returns:
        List of ticker symbols
    """
    if use_full_sp500:
        return fetch_sp500_tickers()
    return SP500_SAMPLE
