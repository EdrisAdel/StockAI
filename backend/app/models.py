from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKeyConstraint, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PriceDaily(Base):
    __tablename__ = "prices_daily"

    ticker: Mapped[str] = mapped_column(String, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    adj_close: Mapped[float | None] = mapped_column(Numeric(18, 6))
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source: Mapped[str] = mapped_column(String, default="yfinance")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FundamentalDaily(Base):
    __tablename__ = "fundamentals_daily"

    ticker: Mapped[str] = mapped_column(String, primary_key=True)
    as_of_date: Mapped[date] = mapped_column(Date, primary_key=True)
    market_cap: Mapped[float | None] = mapped_column(Numeric(20, 2))
    trailing_pe: Mapped[float | None] = mapped_column(Numeric(18, 6))
    forward_pe: Mapped[float | None] = mapped_column(Numeric(18, 6))
    avg_volume: Mapped[int | None] = mapped_column(BigInteger)
    sector: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String, default="yfinance")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IndicatorDaily(Base):
    __tablename__ = "indicators_daily"

    ticker: Mapped[str] = mapped_column(String, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    sma_20: Mapped[float | None] = mapped_column(Numeric(18, 6))
    sma_50: Mapped[float | None] = mapped_column(Numeric(18, 6))
    rsi_14: Mapped[float | None] = mapped_column(Numeric(18, 6))
    vol_20: Mapped[float | None] = mapped_column(Numeric(18, 6))
    ret_1d: Mapped[float | None] = mapped_column(Numeric(18, 8))
    ret_20d: Mapped[float | None] = mapped_column(Numeric(18, 8))
    macd: Mapped[float | None] = mapped_column(Numeric(18, 8))
    macd_signal: Mapped[float | None] = mapped_column(Numeric(18, 8))
    macd_hist: Mapped[float | None] = mapped_column(Numeric(18, 8))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        ForeignKeyConstraint(["ticker", "trade_date"], ["prices_daily.ticker", "prices_daily.trade_date"], ondelete="CASCADE"),
    )


class RunLog(Base):
    __tablename__ = "run_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
