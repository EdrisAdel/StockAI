from datetime import date as dt_date
from typing import Literal

from pydantic import BaseModel, Field


class RefreshRequest(BaseModel):
    tickers: list[str] | None = None
    period: str = "2y"
    use_sp500: bool = False
    batch_size: int = Field(default=50, ge=1, le=100)
    delay_seconds: float = Field(default=1.0, ge=0.0, le=10.0)


class TopScreenRequest(BaseModel):
    date: dt_date | None = None
    metric: Literal["ret_20d", "rsi_14", "vol_20", "sma_20", "sma_50", "macd", "macd_hist"] = "ret_20d"
    n: int = Field(default=10, ge=1, le=100)


class AskRequest(BaseModel):
    question: str


class AnalysisIntent(BaseModel):
    action: Literal["top_n_by_metric", "ticker_snapshot", "screen_stocks"]
    metric: Literal["ret_20d", "rsi_14", "vol_20", "sma_20", "sma_50", "macd", "macd_hist"] = "ret_20d"
    n: int = Field(default=10, ge=1, le=100)
    date: dt_date | None = None
    ticker: str | None = None


class FilterCondition(BaseModel):
    field: Literal[
        "rsi_14",
        "ret_20d",
        "vol_20",
        "sma_20",
        "sma_50",
        "macd",
        "macd_signal",
        "macd_hist",
        "trailing_pe",
        "forward_pe",
        "market_cap",
        "avg_volume",
        "sector",
    ]
    op: Literal[">", ">=", "<", "<=", "=", "!=", "in"]
    value: float | str | list[str]


class StockScreenIntent(BaseModel):
    action: Literal["screen_stocks", "top_n_by_metric", "ticker_snapshot"] = "screen_stocks"
    filters: list[FilterCondition] = Field(default_factory=list)
    sort_by: Literal[
        "ret_20d",
        "rsi_14",
        "vol_20",
        "sma_20",
        "sma_50",
        "macd",
        "macd_hist",
        "trailing_pe",
        "forward_pe",
        "market_cap",
        "avg_volume",
    ] = "ret_20d"
    sort_order: Literal["asc", "desc"] = "desc"
    n: int = Field(default=10, ge=1, le=100)
    date: dt_date | None = None
    ticker: str | None = None


class RangeFilter(BaseModel):
    field: str
    min: float | None = None
    max: float | None = None


class ManualScreenRequest(BaseModel):
    filters: list[RangeFilter] = Field(default_factory=list)
    sectors: list[str] | None = Field(default_factory=list)
    sort_by: str = "ret_20d"
    sort_order: Literal["asc", "desc"] = "desc"
    n: int = Field(default=50, ge=1, le=200)


class StockDetailRequest(BaseModel):
    ticker: str
    period: Literal["1W", "1M", "3M", "1Y", "2Y"] = "1M"


class DailyMoversRequest(BaseModel):
    n: int = Field(default=10, ge=1, le=50)
