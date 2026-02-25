# StockAI — AI-Powered Equity Screening Platform

> Screen 500+ S&P 500 stocks using plain English. No finance degree required.

**[Live Demo](https://stockai-project.vercel.app)** · **[Backend API](https://stockai-production-0f6c.up.railway.app/docs)**

---

## Overview

StockAI is a full-stack stock screening platform that lets users find equities using natural language instead of manual filters. Type something like *"oversold tech stocks with strong earnings momentum"* and StockAI maps that to real quantitative indicators — RSI, MACD, P/E ratios — runs the query across 500+ S&P 500 equities, and returns ranked results in real time.

Built to demonstrate end-to-end product development across data engineering, machine learning, backend systems, and AI integration.

![Demo GIF](./assets/stockai.gif)

---

## Features

- **Natural Language Screener** — GPT-4 powered query interface that translates plain English investment criteria into structured filter logic across technical and fundamental indicators
- **Quantitative Indicator Engine** — Daily computation of RSI, MACD, Bollinger Bands, 50/200-day moving averages, and volume trends across all 500 equities
- **Stock Detail View** — Interactive price charts, full indicator breakdown, key fundamentals, and an AI-generated plain English summary per stock
- **Automated Data Pipeline** — Daily ingestion of OHLCV and fundamental data via yFinance with APScheduler, keeping all indicators current
- **Manual Filter Screener** — Traditional range-based filtering alongside the AI interface for full control
- **Watchlist** — Save and track stocks with performance since added
- **Market Movers Dashboard** — Top gainers, losers, and most oversold stocks updated daily

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, Recharts, Vercel |
| Backend | Python, FastAPI, Docker, Railway |
| Database | PostgreSQL (Supabase) |
| Caching | Redis |
| AI / NLP | OpenAI GPT-4, LangChain |
| Data Ingestion | yFinance, Pandas, APScheduler |
| ORM | SQLAlchemy |

---

## Architecture

```
User → React (Vercel)
          ↓
     FastAPI Backend (Railway)
          ↓               ↓
   Redis Cache       APScheduler
                         ↓
              PostgreSQL (Supabase)
                         ↓
                      yFinance
                         ↓
                    OpenAI API
```

The backend exposes three core endpoints:

- `POST /screen/natural` — Accepts a plain English query, uses GPT-4 + LangChain to parse it into filter logic, and returns ranked results
- `GET /screen/filter` — Traditional filter endpoint accepting RSI, P/E, sector, and momentum parameters
- `GET /stock/{ticker}` — Returns full indicator profile, fundamentals, and AI-generated summary for a single equity

APScheduler runs a nightly job at market close to refresh all OHLCV data and recompute indicators for all 500 equities.

---

## Data & Indicators

**Universe:** S&P 500 (500 equities)

**Data sources:** yFinance (OHLCV, fundamentals)

**Computed indicators:**

| Indicator | Description |
|---|---|
| RSI (14) | Relative Strength Index — momentum oscillator |
| MACD | Moving Average Convergence Divergence |
| Bollinger Bands | Volatility bands around 20-day SMA |
| SMA 50 / SMA 200 | Short and long-term trend signals |
| Volume Trend | 20-day average volume vs current |
| P/E Ratio | Price-to-earnings (trailing) |
| Revenue Growth | YoY revenue growth rate |

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL instance (or Supabase project)
- OpenAI API key

### Backend

```bash
git clone https://github.com/EdrisAdel/StockAI.git
cd StockAI/backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Fill in: DATABASE_URL, OPENAI_API_KEY, REDIS_URL

# Run migrations
alembic upgrade head

# Seed initial data (pulls S&P 500 data from yFinance)
python scripts/seed.py

# Start the server
uvicorn main:app --reload
```

### Frontend

```bash
cd StockAI/frontend

npm install

# Set environment variable
echo "VITE_API_URL=http://localhost:8000" > .env.local

npm run dev
```

---

## Project Structure

```
StockAI/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── routers/
│   │   ├── screen.py        # Screener endpoints
│   │   └── stocks.py        # Stock detail endpoints
│   ├── services/
│   │   ├── ai.py            # GPT-4 + LangChain query parsing
│   │   ├── indicators.py    # Pandas indicator computation
│   │   └── pipeline.py      # yFinance ingestion + scheduler
│   ├── models/              # SQLAlchemy models
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/           # Home, Screener, Detail, Watchlist
│   │   ├── components/      # Shared UI components
│   │   └── api/             # API client
│   └── package.json
└── README.md
```

---

## Deployment

| Service | Platform | Notes |
|---|---|---|
| Frontend | Vercel | Auto-deploys on push to `main` |
| Backend + Redis | Railway | Dockerized, Redis add-on |
| Database | Supabase | Managed PostgreSQL |

---

## Roadmap

- [ ] Email alerts for watchlist stocks hitting RSI thresholds
- [ ] Portfolio backtester — run a strategy against historical data
- [ ] TSX 60 support for Canadian equities
- [ ] Earnings calendar integration

---

## Author

**Edris Adel** — [edrisadel.dev](https://edrisadel.dev) · [LinkedIn](https://linkedin.com/in/edrisadel) · [GitHub](https://github.com/EdrisAdel)
License MIT
