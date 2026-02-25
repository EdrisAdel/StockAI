from datetime import date, datetime, timedelta

from sqlalchemy import and_, asc, desc, func, select
from sqlalchemy.orm import Session

from app.models import FundamentalDaily, IndicatorDaily, PriceDaily
from app.schemas import ManualScreenRequest, RangeFilter


def get_stock_detail(db: Session, ticker: str, period: str = "1M"):
    ticker = ticker.upper()
    
    # Get period range
    period_map = {"1W": 7, "1M": 30, "3M": 90, "1Y": 365, "2Y": 730}
    days = period_map.get(period, 30)
    
    latest_date = db.scalar(select(func.max(PriceDaily.trade_date)).where(PriceDaily.ticker == ticker))
    if not latest_date:
        return None
    
    start_date = latest_date - timedelta(days=days)
    
    # Historical prices
    prices_query = (
        select(PriceDaily)
        .where(PriceDaily.ticker == ticker)
        .where(PriceDaily.trade_date >= start_date)
        .order_by(PriceDaily.trade_date)
    )
    prices = db.execute(prices_query).scalars().all()
    
    # Historical indicators
    indicators_query = (
        select(IndicatorDaily)
        .where(IndicatorDaily.ticker == ticker)
        .where(IndicatorDaily.trade_date >= start_date)
        .order_by(IndicatorDaily.trade_date)
    )
    indicators = db.execute(indicators_query).scalars().all()
    
    # Latest fundamentals
    latest_fund_date_sq = (
        select(func.max(FundamentalDaily.as_of_date))
        .where(FundamentalDaily.ticker == ticker)
        .scalar_subquery()
    )
    fundamentals = db.execute(
        select(FundamentalDaily)
        .where(FundamentalDaily.ticker == ticker)
        .where(FundamentalDaily.as_of_date == latest_fund_date_sq)
    ).scalar_one_or_none()
    
    # Build response
    price_history = []
    for p in prices:
        price_history.append({
            "date": p.trade_date,
            "open": float(p.open),
            "high": float(p.high),
            "low": float(p.low),
            "close": float(p.close),
            "adj_close": float(p.adj_close) if p.adj_close else None,
            "volume": int(p.volume),
        })
    
    indicator_history = []
    for ind in indicators:
        indicator_history.append({
            "date": ind.trade_date,
            "sma_20": float(ind.sma_20) if ind.sma_20 is not None else None,
            "sma_50": float(ind.sma_50) if ind.sma_50 is not None else None,
            "rsi_14": float(ind.rsi_14) if ind.rsi_14 is not None else None,
            "vol_20": float(ind.vol_20) if ind.vol_20 is not None else None,
            "ret_1d": float(ind.ret_1d) if ind.ret_1d is not None else None,
            "ret_20d": float(ind.ret_20d) if ind.ret_20d is not None else None,
            "macd": float(ind.macd) if ind.macd is not None else None,
            "macd_signal": float(ind.macd_signal) if ind.macd_signal is not None else None,
            "macd_hist": float(ind.macd_hist) if ind.macd_hist is not None else None,
        })
    
    fundamentals_dict = None
    if fundamentals:
        fundamentals_dict = {
            "as_of_date": fundamentals.as_of_date,
            "market_cap": float(fundamentals.market_cap) if fundamentals.market_cap else None,
            "trailing_pe": float(fundamentals.trailing_pe) if fundamentals.trailing_pe else None,
            "forward_pe": float(fundamentals.forward_pe) if fundamentals.forward_pe else None,
            "avg_volume": int(fundamentals.avg_volume) if fundamentals.avg_volume else None,
            "sector": fundamentals.sector,
        }
    
    return {
        "ticker": ticker,
        "latest_date": latest_date,
        "period": period,
        "price_history": price_history,
        "indicator_history": indicator_history,
        "fundamentals": fundamentals_dict,
    }


def execute_manual_screener(db: Session, request: ManualScreenRequest):
    latest_date = db.scalar(select(func.max(IndicatorDaily.trade_date)))
    if not latest_date:
        return []
    
    latest_fund_date_sq = (
        select(FundamentalDaily.ticker, func.max(FundamentalDaily.as_of_date).label("max_as_of_date"))
        .group_by(FundamentalDaily.ticker)
        .subquery()
    )
    
    query = (
        select(
            IndicatorDaily.ticker,
            IndicatorDaily.trade_date,
            IndicatorDaily.rsi_14,
            IndicatorDaily.ret_20d,
            IndicatorDaily.vol_20,
            IndicatorDaily.sma_20,
            IndicatorDaily.sma_50,
            IndicatorDaily.macd,
            IndicatorDaily.macd_signal,
            IndicatorDaily.macd_hist,
            FundamentalDaily.trailing_pe,
            FundamentalDaily.forward_pe,
            FundamentalDaily.market_cap,
            FundamentalDaily.avg_volume,
            FundamentalDaily.sector,
        )
        .join(
            latest_fund_date_sq,
            latest_fund_date_sq.c.ticker == IndicatorDaily.ticker,
            isouter=True,
        )
        .join(
            FundamentalDaily,
            and_(
                FundamentalDaily.ticker == latest_fund_date_sq.c.ticker,
                FundamentalDaily.as_of_date == latest_fund_date_sq.c.max_as_of_date,
            ),
            isouter=True,
        )
        .where(IndicatorDaily.trade_date == latest_date)
    )
    
    # Apply range filters
    field_map = {
        "rsi_14": IndicatorDaily.rsi_14,
        "ret_20d": IndicatorDaily.ret_20d,
        "vol_20": IndicatorDaily.vol_20,
        "sma_20": IndicatorDaily.sma_20,
        "sma_50": IndicatorDaily.sma_50,
        "macd": IndicatorDaily.macd,
        "macd_signal": IndicatorDaily.macd_signal,
        "macd_hist": IndicatorDaily.macd_hist,
        "trailing_pe": FundamentalDaily.trailing_pe,
        "forward_pe": FundamentalDaily.forward_pe,
        "market_cap": FundamentalDaily.market_cap,
        "avg_volume": FundamentalDaily.avg_volume,
    }
    
    for rf in request.filters:
        if rf.field not in field_map:
            continue
        col = field_map[rf.field]
        if rf.min is not None:
            query = query.where(col >= rf.min)
        if rf.max is not None:
            query = query.where(col <= rf.max)
    
    # Apply sector filter
    if request.sectors:
        query = query.where(FundamentalDaily.sector.in_(request.sectors))
    
    # Apply sorting
    if request.sort_by in field_map:
        sort_col = field_map[request.sort_by]
        order_clause = desc(sort_col) if request.sort_order == "desc" else asc(sort_col)
        query = query.order_by(order_clause)
    
    query = query.limit(request.n)
    rows = db.execute(query).all()
    
    result = []
    for row in rows:
        result.append({
            "ticker": row.ticker,
            "date": row.trade_date,
            "rsi_14": float(row.rsi_14) if row.rsi_14 is not None else None,
            "ret_20d": float(row.ret_20d) if row.ret_20d is not None else None,
            "vol_20": float(row.vol_20) if row.vol_20 is not None else None,
            "sma_20": float(row.sma_20) if row.sma_20 is not None else None,
            "sma_50": float(row.sma_50) if row.sma_50 is not None else None,
            "macd": float(row.macd) if row.macd is not None else None,
            "macd_signal": float(row.macd_signal) if row.macd_signal is not None else None,
            "macd_hist": float(row.macd_hist) if row.macd_hist is not None else None,
            "trailing_pe": float(row.trailing_pe) if row.trailing_pe is not None else None,
            "forward_pe": float(row.forward_pe) if row.forward_pe is not None else None,
            "market_cap": float(row.market_cap) if row.market_cap is not None else None,
            "avg_volume": int(row.avg_volume) if row.avg_volume is not None else None,
            "sector": row.sector,
        })
    
    return result


def get_daily_movers(db: Session, n: int = 10):
    latest_date = db.scalar(select(func.max(IndicatorDaily.trade_date)))
    if not latest_date:
        return {"gainers": [], "losers": [], "oversold": []}
    
    # Top gainers
    gainers = db.execute(
        select(IndicatorDaily.ticker, IndicatorDaily.ret_1d)
        .where(IndicatorDaily.trade_date == latest_date)
        .where(IndicatorDaily.ret_1d.is_not(None))
        .order_by(desc(IndicatorDaily.ret_1d))
        .limit(n)
    ).all()
    
    # Top losers
    losers = db.execute(
        select(IndicatorDaily.ticker, IndicatorDaily.ret_1d)
        .where(IndicatorDaily.trade_date == latest_date)
        .where(IndicatorDaily.ret_1d.is_not(None))
        .order_by(IndicatorDaily.ret_1d)
        .limit(n)
    ).all()
    
    # Oversold (RSI < 30)
    oversold = db.execute(
        select(IndicatorDaily.ticker, IndicatorDaily.rsi_14)
        .where(IndicatorDaily.trade_date == latest_date)
        .where(IndicatorDaily.rsi_14 < 30)
        .order_by(IndicatorDaily.rsi_14)
        .limit(n)
    ).all()
    
    return {
        "gainers": [{"ticker": r.ticker, "ret_1d": float(r.ret_1d)} for r in gainers],
        "losers": [{"ticker": r.ticker, "ret_1d": float(r.ret_1d)} for r in losers],
        "oversold": [{"ticker": r.ticker, "rsi_14": float(r.rsi_14)} for r in oversold],
    }


PRESET_SCREENERS = {
    "undervalued_growth": {
        "name": "Undervalued Growth Stocks",
        "description": "Low P/E with strong recent returns",
        "filters": [
            {"field": "forward_pe", "min": None, "max": 25},
            {"field": "ret_20d", "min": 0.05, "max": None},
        ],
        "sort_by": "ret_20d",
        "sort_order": "desc",
    },
    "high_momentum": {
        "name": "High Momentum",
        "description": "Strong 20-day returns with positive MACD",
        "filters": [
            {"field": "ret_20d", "min": 0.1, "max": None},
            {"field": "macd_hist", "min": 0, "max": None},
        ],
        "sort_by": "ret_20d",
        "sort_order": "desc",
    },
    "oversold_value": {
        "name": "Oversold Value Plays",
        "description": "Low RSI with reasonable valuation",
        "filters": [
            {"field": "rsi_14", "min": None, "max": 35},
            {"field": "trailing_pe", "min": None, "max": 30},
        ],
        "sort_by": "rsi_14",
        "sort_order": "asc",
    },
}


def get_preset_screener(db: Session, preset_name: str, n: int = 50):
    if preset_name not in PRESET_SCREENERS:
        return None
    
    preset = PRESET_SCREENERS[preset_name]
    filters = [RangeFilter(**f) for f in preset["filters"]]
    
    request = ManualScreenRequest(
        filters=filters,
        sort_by=preset["sort_by"],
        sort_order=preset["sort_order"],
        n=n,
    )
    
    return {
        "name": preset["name"],
        "description": preset["description"],
        "results": execute_manual_screener(db, request),
    }
