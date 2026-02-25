from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.schemas import AskRequest, ManualScreenRequest, RefreshRequest, TopScreenRequest
from app.scheduler import start_scheduler
from app.services.analytics import execute_stock_screen, ticker_snapshot, top_n_by_metric
from app.services.analytics_extended import (
    execute_manual_screener,
    get_daily_movers,
    get_preset_screener,
    get_stock_detail,
)
from app.services.cache import cache_get, cache_set
from app.services.ingestion import refresh_prices_and_fundamentals
from app.services.llm import build_nl_answer, question_to_intent
from app.services.universe import get_universe


Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

configured_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    with engine.begin() as conn:
        conn.execute(text("alter table if exists fundamentals_daily add column if not exists sector text"))
        conn.execute(text("alter table if exists indicators_daily add column if not exists macd numeric(18,8)"))
        conn.execute(text("alter table if exists indicators_daily add column if not exists macd_signal numeric(18,8)"))
        conn.execute(text("alter table if exists indicators_daily add column if not exists macd_hist numeric(18,8)"))

    start_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/refresh")
def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    if request.tickers:
        tickers = request.tickers
    elif request.use_sp500:
        tickers = get_universe(use_full_sp500=True)
    else:
        tickers = get_universe(use_full_sp500=False)
    
    stats = refresh_prices_and_fundamentals(
        db=db,
        tickers=tickers,
        period=request.period,
        batch_size=request.batch_size,
        delay_seconds=request.delay_seconds,
    )
    return {"ok": True, "stats": stats}


@app.post("/screen/top")
def screen_top(request: TopScreenRequest, db: Session = Depends(get_db)):
    cache_key = f"top:{request.metric}:{request.date}:{request.n}"
    cached = cache_get(cache_key)
    if cached is not None:
        return {"cached": True, "rows": cached}

    rows = top_n_by_metric(db=db, metric=request.metric, n=request.n, target_date=request.date)
    cache_set(cache_key, rows, ttl_seconds=300)
    return {"cached": False, "rows": rows}


@app.get("/ticker/{ticker}")
def get_ticker(ticker: str, db: Session = Depends(get_db)):
    cache_key = f"ticker:{ticker.upper()}"
    cached = cache_get(cache_key)
    if cached is not None:
        return {"cached": True, "row": cached}

    row = ticker_snapshot(db=db, ticker=ticker.upper())
    if row is None:
        raise HTTPException(status_code=404, detail="Ticker not found")

    cache_set(cache_key, row, ttl_seconds=120)
    return {"cached": False, "row": row}


@app.post("/ask")
def ask(request: AskRequest, db: Session = Depends(get_db)):
    intent = question_to_intent(request.question)

    if intent.action == "screen_stocks":
        screen_response = execute_stock_screen(db=db, intent=intent)
        rows = screen_response["rows"]
        answer = build_nl_answer(request.question, intent, rows)
        return {
            "intent": intent.model_dump(),
            "result": rows,
            "answer": answer,
            "execution": screen_response["execution"],
            "guardrails": {
                "mode": "structured_filters_only",
                "ticker_hallucination_blocked": True,
                "unknown_fields_blocked": True,
            },
        }

    if intent.action == "top_n_by_metric":
        top_metric = intent.sort_by if intent.sort_by in {"ret_20d", "rsi_14", "vol_20", "sma_20", "sma_50", "macd", "macd_hist"} else "ret_20d"
        rows = top_n_by_metric(db=db, metric=top_metric, n=intent.n, target_date=intent.date)
        answer = build_nl_answer(request.question, intent, rows)
        return {"intent": intent.model_dump(), "result": rows, "answer": answer}

    if intent.action == "ticker_snapshot":
        if not intent.ticker:
            raise HTTPException(status_code=400, detail="ticker is required for ticker_snapshot")
        row = ticker_snapshot(db=db, ticker=intent.ticker.upper())
        if row is None:
            raise HTTPException(status_code=404, detail="Ticker not found in database")
        answer = f"Snapshot for {row['ticker']} on {row['date']}: close={row['close']}, volume={row['volume']}."
        return {"intent": intent.model_dump(), "result": row, "answer": answer}

    raise HTTPException(status_code=400, detail="Unsupported action")


@app.get("/stock/{ticker}/detail")
def stock_detail(ticker: str, period: str = Query("1M", regex="^(1W|1M|3M|1Y|2Y)$"), db: Session = Depends(get_db)):
    cache_key = f"detail:{ticker.upper()}:{period}"
    cached = cache_get(cache_key)
    if cached is not None:
        return {"cached": True, **cached}
    
    detail = get_stock_detail(db=db, ticker=ticker, period=period)
    if detail is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    cache_set(cache_key, detail, ttl_seconds=300)
    return {"cached": False, **detail}


@app.post("/screen/manual")
def manual_screen(request: ManualScreenRequest, db: Session = Depends(get_db)):
    results = execute_manual_screener(db=db, request=request)
    return {"results": results, "count": len(results)}


@app.get("/movers")
def daily_movers(n: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    cache_key = f"movers:{n}"
    cached = cache_get(cache_key)
    if cached is not None:
        return {"cached": True, **cached}
    
    movers = get_daily_movers(db=db, n=n)
    cache_set(cache_key, movers, ttl_seconds=300)
    return {"cached": False, **movers}


@app.get("/presets/{preset_name}")
def preset_screen(preset_name: str, n: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    cache_key = f"preset:{preset_name}:{n}"
    cached = cache_get(cache_key)
    if cached is not None:
        return {"cached": True, **cached}
    
    result = get_preset_screener(db=db, preset_name=preset_name, n=n)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_name}' not found")
    
    cache_set(cache_key, result, ttl_seconds=300)
    return {"cached": False, **result}

