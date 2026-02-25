import logging
import time
from datetime import UTC, datetime

import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import FundamentalDaily, IndicatorDaily, PriceDaily
from app.services.universe import SECTOR_FALLBACK

logger = logging.getLogger(__name__)


def _flatten_prices(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()

    # yfinance with group_by="ticker" returns MultiIndex columns (Ticker, Price)
    if isinstance(raw.columns, pd.MultiIndex):
        # Stack to convert wide format to long format
        # After stack, we'll have index (Date, Ticker) and columns (Price metrics)
        frame = raw.stack(level=0, future_stack=True)
        frame = frame.reset_index()
        
        # Rename columns
        frame = frame.rename(columns={
            "Date": "trade_date",
            "level_1": "ticker",
            "Ticker": "ticker",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        })
    else:
        # Fallback for simple column structure (shouldn't happen with group_by="ticker")
        t = tickers[0]
        frame = raw.copy()
        frame = frame.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        })
        frame["ticker"] = t
        frame = frame.reset_index().rename(columns={"Date": "trade_date"})
    
    # Ensure required columns exist
    required = ["ticker", "trade_date", "open", "high", "low", "close", "adj_close", "volume"]
    available = frame.columns.tolist()
    
    if not all(col in available for col in required):
        logger.warning(f"Missing columns. Required: {required}, Available: {available}")
        return pd.DataFrame()
    
    return frame[required]


def _compute_indicators(prices: pd.DataFrame) -> pd.DataFrame:
    if prices.empty:
        return pd.DataFrame()

    out = []
    prices = prices.sort_values(["ticker", "trade_date"])  # noqa: PD002
    for ticker, group in prices.groupby("ticker"):
        g = group.copy()
        g["ret_1d"] = g["close"].pct_change(1)
        g["ret_20d"] = g["close"].pct_change(20)
        g["sma_20"] = g["close"].rolling(20).mean()
        g["sma_50"] = g["close"].rolling(50).mean()
        delta = g["close"].diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = (-delta.clip(upper=0)).rolling(14).mean()
        rs = up / down.replace(0, pd.NA)
        g["rsi_14"] = 100 - (100 / (1 + rs))
        g["vol_20"] = g["ret_1d"].rolling(20).std() * (252**0.5)
        ema_12 = g["close"].ewm(span=12, adjust=False).mean()
        ema_26 = g["close"].ewm(span=26, adjust=False).mean()
        g["macd"] = ema_12 - ema_26
        g["macd_signal"] = g["macd"].ewm(span=9, adjust=False).mean()
        g["macd_hist"] = g["macd"] - g["macd_signal"]
        out.append(g)

    res = pd.concat(out, ignore_index=True)
    return res[
        [
            "ticker",
            "trade_date",
            "sma_20",
            "sma_50",
            "rsi_14",
            "vol_20",
            "ret_1d",
            "ret_20d",
            "macd",
            "macd_signal",
            "macd_hist",
        ]
    ]


def _refresh_batch(
    db: Session,
    tickers: list[str],
    period: str,
    batch_num: int,
    total_batches: int,
) -> dict:
    """
    Refresh a single batch of tickers.
    """
    logger.info(f"Processing batch {batch_num}/{total_batches} ({len(tickers)} tickers)")
    
    raw = yf.download(
        tickers=tickers,
        period=period,
        auto_adjust=False,
        group_by="ticker",
        progress=False,
        threads=True,
    )
    prices = _flatten_prices(raw, tickers)
    prices = prices.dropna(subset=["open", "high", "low", "close", "volume"])
    prices["trade_date"] = pd.to_datetime(prices["trade_date"]).dt.date

    price_rows = prices.to_dict(orient="records")
    if price_rows:
        stmt = insert(PriceDaily).values(price_rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[PriceDaily.ticker, PriceDaily.trade_date],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "adj_close": stmt.excluded.adj_close,
                "volume": stmt.excluded.volume,
                "updated_at": datetime.now(UTC),
            },
        )
        db.execute(stmt)

    run_date = datetime.now(UTC).date()
    fundamentals = []
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info or {}
            fundamentals.append(
                {
                    "ticker": ticker,
                    "as_of_date": run_date,
                    "market_cap": info.get("marketCap"),
                    "trailing_pe": info.get("trailingPE"),
                    "forward_pe": info.get("forwardPE"),
                    "avg_volume": info.get("averageVolume"),
                    "sector": info.get("sector") or SECTOR_FALLBACK.get(ticker),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to fetch fundamentals for {ticker}: {e}")
            continue

    if fundamentals:
        f_stmt = insert(FundamentalDaily).values(fundamentals)
        f_stmt = f_stmt.on_conflict_do_update(
            index_elements=[FundamentalDaily.ticker, FundamentalDaily.as_of_date],
            set_={
                "market_cap": f_stmt.excluded.market_cap,
                "trailing_pe": f_stmt.excluded.trailing_pe,
                "forward_pe": f_stmt.excluded.forward_pe,
                "avg_volume": f_stmt.excluded.avg_volume,
                "sector": f_stmt.excluded.sector,
                "updated_at": datetime.now(UTC),
            },
        )
        db.execute(f_stmt)

    indicators = _compute_indicators(prices)
    indicator_rows = indicators.where(pd.notnull(indicators), None).to_dict(orient="records")
    if indicator_rows:
        i_stmt = insert(IndicatorDaily).values(indicator_rows)
        i_stmt = i_stmt.on_conflict_do_update(
            index_elements=[IndicatorDaily.ticker, IndicatorDaily.trade_date],
            set_={
                "sma_20": i_stmt.excluded.sma_20,
                "sma_50": i_stmt.excluded.sma_50,
                "rsi_14": i_stmt.excluded.rsi_14,
                "vol_20": i_stmt.excluded.vol_20,
                "ret_1d": i_stmt.excluded.ret_1d,
                "ret_20d": i_stmt.excluded.ret_20d,
                "macd": i_stmt.excluded.macd,
                "macd_signal": i_stmt.excluded.macd_signal,
                "macd_hist": i_stmt.excluded.macd_hist,
                "updated_at": datetime.now(UTC),
            },
        )
        db.execute(i_stmt)

    db.commit()
    
    return {
        "price_rows": len(price_rows),
        "fundamental_rows": len(fundamentals),
        "indicator_rows": len(indicator_rows),
    }


def refresh_prices_and_fundamentals(
    db: Session,
    tickers: list[str],
    period: str = "2y",
    batch_size: int = 50,
    delay_seconds: float = 1.0,
) -> dict:
    """
    Refresh prices and fundamentals for a list of tickers.
    
    Args:
        db: Database session
        tickers: List of ticker symbols
        period: Data period (e.g., '2y', '1y', '6mo')
        batch_size: Number of tickers to process per batch
        delay_seconds: Delay between batches to avoid rate limits
    
    Returns:
        Statistics dictionary with counts
    """
    start_time = time.time()
    total_stats = {
        "tickers": len(tickers),
        "price_rows": 0,
        "fundamental_rows": 0,
        "indicator_rows": 0,
        "batches_processed": 0,
        "duration_seconds": 0,
    }
    
    # Split tickers into batches
    batches = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]
    total_batches = len(batches)
    
    logger.info(f"Starting refresh for {len(tickers)} tickers in {total_batches} batches")
    
    for batch_num, batch in enumerate(batches, 1):
        try:
            batch_stats = _refresh_batch(db, batch, period, batch_num, total_batches)
            total_stats["price_rows"] += batch_stats["price_rows"]
            total_stats["fundamental_rows"] += batch_stats["fundamental_rows"]
            total_stats["indicator_rows"] += batch_stats["indicator_rows"]
            total_stats["batches_processed"] += 1
            
            # Rate limiting delay between batches (except after last batch)
            if batch_num < total_batches:
                logger.info(f"Waiting {delay_seconds}s before next batch...")
                time.sleep(delay_seconds)
        
        except Exception as e:
            logger.error(f"Error processing batch {batch_num}: {e}")
            # Continue with next batch even if one fails
            continue
    
    total_stats["duration_seconds"] = round(time.time() - start_time, 2)
    logger.info(
        f"Refresh complete: {total_stats['tickers']} tickers, "
        f"{total_stats['price_rows']} prices, "
        f"{total_stats['fundamental_rows']} fundamentals, "
        f"{total_stats['indicator_rows']} indicators in "
        f"{total_stats['duration_seconds']}s"
    )
    
    return total_stats
