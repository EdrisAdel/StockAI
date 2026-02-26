import { useEffect, useRef, useState } from "react";
import { HiChartBar } from "react-icons/hi";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  askQuestion,
  getDailyMovers,
  getPreset,
  getStockDetail,
} from "./api";

/* ───────── helpers ───────── */

function fmtCap(v) {
  if (!v) return "—";
  if (v >= 1e12) return `${(v / 1e12).toFixed(1)}T`;
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(0)}M`;
  return v.toLocaleString();
}

function fmtPct(v) {
  if (v == null) return "—";
  const p = (v * 100).toFixed(2);
  return v >= 0 ? `+${p}%` : `${p}%`;
}

function fmtDate(d) {
  if (!d) return "";
  return new Date(d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/* ───────── presets config ───────── */

const presets = [
  { key: "high_momentum", label: "High Momentum", desc: "Strong 20-day returns with positive MACD" },
  { key: "undervalued_growth", label: "Undervalued Growth", desc: "Low P/E with strong recent returns" },
  { key: "oversold_value", label: "Oversold Value", desc: "Low RSI with reasonable valuation" }
  // { key: "tech_earners", label: "Tech Earners", desc: "Technology stocks with strong earnings" },
];

const sampleQueries = [
  "Show me oversold tech stocks with strong earnings",
  "Large cap stocks with P/E under 25",
  "High momentum stocks with RSI above 65",
  "Which stocks have gained the most in the last 20 days?",
];

function HomeSkeleton() {
  return (
    <div className="page-col skeleton-page">
      <div className="hero">
        <div className="skeleton-line skeleton-title" />
        <div className="skeleton-line skeleton-subtitle" />
        <div className="skeleton-input" />
      </div>
      <div className="card">
        <div className="skeleton-line skeleton-card-title" />
        <div className="skeleton-grid-2">
          <div>
            <div className="skeleton-line skeleton-label" />
            <div className="skeleton-list">
              {[...Array(4)].map((_, index) => (
                <div key={index} className="skeleton-pill" />
              ))}
            </div>
          </div>
          <div>
            <div className="skeleton-line skeleton-label" />
            <div className="skeleton-list">
              {[...Array(4)].map((_, index) => (
                <div key={index} className="skeleton-pill" />
              ))}
            </div>
          </div>
        </div>
      </div>
      <div>
        <div className="skeleton-line skeleton-card-title" style={{ width: 140, marginBottom: 14 }} />
        <div className="skeleton-grid-3">
          {[...Array(3)].map((_, index) => (
            <div key={index} className="skeleton-block" />
          ))}
        </div>
      </div>
    </div>
  );
}

function ScreenerSkeleton() {
  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      <div className="table-header-bar">
        <div className="skeleton-line" style={{ width: 90, height: 14 }} />
      </div>
      <div style={{ padding: "0 24px" }}>
        <div className="table-cols">
          {[...Array(5)].map((_, index) => (
            <div key={index} className="skeleton-line" style={{ flex: 1, height: 10, marginRight: 12 }} />
          ))}
          <div style={{ width: 40 }} />
        </div>
        {[...Array(7)].map((_, index) => (
          <div key={index} className="skeleton-row">
            <div style={{ flex: 2 }}>
              <div className="skeleton-line" style={{ width: 80, marginBottom: 8 }} />
              <div className="skeleton-line" style={{ width: 140, height: 10 }} />
            </div>
            <div className="skeleton-line" style={{ flex: 1, height: 22, borderRadius: 999 }} />
            <div className="skeleton-line" style={{ flex: 1, marginLeft: 16 }} />
            <div className="skeleton-line" style={{ flex: 1, marginLeft: 16 }} />
            <div className="skeleton-line" style={{ flex: 1, marginLeft: 16 }} />
            <div className="skeleton-line" style={{ width: 32, height: 32, borderRadius: 999, marginLeft: 16 }} />
          </div>
        ))}
      </div>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="page-col skeleton-page">
      <div className="card">
        <div className="skeleton-line" style={{ width: 140, height: 30, marginBottom: 10 }} />
        <div className="skeleton-line" style={{ width: 220, height: 12 }} />
      </div>
      <div className="card">
        <div className="skeleton-line" style={{ width: 120, marginBottom: 16 }} />
        <div className="skeleton-chart" />
      </div>
      <div className="stats-grid">
        {[...Array(8)].map((_, index) => (
          <div key={index} className="stat-box">
            <div className="skeleton-line" style={{ width: "50%", margin: "0 auto 10px", height: 10 }} />
            <div className="skeleton-line" style={{ width: "70%", margin: "0 auto", height: 18 }} />
          </div>
        ))}
      </div>
    </div>
  );
}

function WatchlistSkeleton() {
  return (
    <div className="page-col skeleton-page">
      <div className="skeleton-line" style={{ width: 180, height: 28 }} />
      <div className="card" style={{ padding: 0 }}>
        <div style={{ padding: "0 24px" }}>
          {[...Array(6)].map((_, index) => (
            <div key={index} className="skeleton-row">
              <div className="skeleton-line" style={{ width: 44, height: 44, borderRadius: 12 }} />
              <div style={{ flex: 2, marginLeft: 14 }}>
                <div className="skeleton-line" style={{ width: 80, marginBottom: 8 }} />
              </div>
              <div className="skeleton-line" style={{ width: 32, height: 32, borderRadius: 999 }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   ROOT COMPONENT
   ═══════════════════════════════════════════ */

export default function App() {
  const [page, setPage] = useState("home");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [aiAnswer, setAiAnswer] = useState("");
  const [selectedTicker, setSelectedTicker] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailPeriod, setDetailPeriod] = useState("1M");
  const [watchlist, setWatchlist] = useState([]);
  const [watchlistLoading, setWatchlistLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [movers, setMovers] = useState(null);
  const [moversLoading, setMoversLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const searchRef = useRef(null);

  useEffect(() => {
    try {
      setWatchlist(JSON.parse(localStorage.getItem("watchlist")) || []);
    } catch {
      setWatchlist([]);
    } finally {
      setWatchlistLoading(false);
    }
  }, []);

  // persist watchlist
  useEffect(() => {
    if (!watchlistLoading) {
      localStorage.setItem("watchlist", JSON.stringify(watchlist));
    }
  }, [watchlist, watchlistLoading]);

  // load movers on mount
  useEffect(() => {
    getDailyMovers(5)
      .then(setMovers)
      .catch(() => {})
      .finally(() => setMoversLoading(false));
  }, []);

  /* ── actions ── */

  async function handleSearch() {
    const q = query.trim();
    if (!q) return;
    setSearching(true);
    setError("");
    setAiAnswer("");
    try {
      const data = await askQuestion(q);
      setResults(data.result ?? []);
      setAiAnswer(data.answer ?? "");
      setPage("screener");
    } catch (e) {
      setError(e.message);
    } finally {
      setSearching(false);
    }
  }

  async function handlePreset(key) {
    setSearching(true);
    setError("");
    setAiAnswer("");
    try {
      const data = await getPreset(key, 50);
      setResults(data.results ?? []);
      setAiAnswer(`Showing preset: ${data.name} — ${data.description}`);
      setPage("screener");
    } catch (e) {
      setError(e.message);
    } finally {
      setSearching(false);
    }
  }

  async function openStock(ticker, period = "1M") {
    setSelectedTicker(ticker);
    setDetailLoading(true);
    setDetail(null);
    setDetailPeriod(period);
    setPage("detail");
    try {
      const data = await getStockDetail(ticker, period);
      setDetail(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setDetailLoading(false);
    }
  }

  function toggleWatchlist(ticker) {
    setWatchlist((prev) =>
      prev.includes(ticker) ? prev.filter((t) => t !== ticker) : [...prev, ticker]
    );
  }

  /* ── nav ── */

  const navItems = [
    { id: "home", label: "Home" },
    { id: "screener", label: "Screener" },
    { id: "watchlist", label: `Watchlist (${watchlist.length})` },
  ];

  /* ═══════════════════════════════════════════
     RENDER
     ═══════════════════════════════════════════ */

  return (
    <div className="shell">
      {/* ─── Navbar ─── */}
      <nav className="navbar">
        <div className="nav-brand" onClick={() => setPage("home")}>
          <div className="logo-icon"><HiChartBar /></div>
          <span className="logo-text">StockAI</span>
        </div>
        <div className="nav-links">
          {navItems.map((n) => (
            <span
              key={n.id}
              className={`nav-link ${page === n.id || (page === "detail" && n.id === "screener") ? "active" : ""}`}
              onClick={() => setPage(n.id)}
            >
              {n.label}
            </span>
          ))}
        </div>
        <span className="market-badge"></span>
          {/* ● Market Open */}
      </nav>


      <div className="container">
        {error && (
          <div className="error-bar" onClick={() => setError("")}>
            ⚠️ {error} <span style={{ float: "right", cursor: "pointer" }}>✕</span>
          </div>
        )}

        {/* ═══════ HOME ═══════ */}
        {page === "home" && (
          moversLoading ? (
            <HomeSkeleton />
          ) : (
          <div className="page-col">
            {/* Hero */}
            <div className="hero">
              <h1 className="hero-title">
                Find stocks in 
                <span className="gradient-text"> plain English</span>
              </h1>
              <p className="hero-sub">
                Query the stock market, get detailed results.
              </p>
              <div className="search-wrap">
                <input
                  ref={searchRef}
                  className="search-input"
                  placeholder="e.g. oversold tech stocks with strong earnings..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
                <button
                  className="btn btn-primary search-btn"
                  onClick={handleSearch}
                  disabled={searching}
                >
                  {searching ? "Searching…" : "Search"}
                </button>
              </div>
              <div className="chips">
                {sampleQueries.map((q) => (
                  <span key={q} className="chip" onClick={() => { setQuery(q); }}>
                    {q}
                  </span>
                ))}
              </div>
            </div>

            {/* Movers */}
            {movers && (
              <div className="card">
                <div className="card-header">
                  <h2 className="card-title">Today's Movers</h2>
                  <span className="muted-sm">{fmtDate(new Date())}</span>
                </div>
                <div className="movers-grid">
                  <div>
                    <p className="label-green">Top Gainers</p>
                    <div className="mover-list">
                      {movers.gainers?.slice(0, 5).map((m) => (
                        <div
                          key={m.ticker}
                          className="mover-pill clickable"
                          onClick={() => openStock(m.ticker)}
                        >
                          <span className="fw700">{m.ticker}</span>
                          <span className="clr-green">{fmtPct(m.ret_1d)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="divider-v" />
                  <div>
                    <p className="label-red">Top Losers</p>
                    <div className="mover-list">
                      {movers.losers?.slice(0, 5).map((m) => (
                        <div
                          key={m.ticker}
                          className="mover-pill clickable"
                          onClick={() => openStock(m.ticker)}
                        >
                          <span className="fw700">{m.ticker}</span>
                          <span className={m.ret_1d >= 0 ? "clr-green" : "clr-red"}>
                            {fmtPct(m.ret_1d)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Presets */}
            <div>
              <h2 className="section-title">Quick Screens</h2>
              <div className="preset-grid">
                {presets.map((p) => (
                  <div
                    key={p.key}
                    className="preset-card"
                    onClick={() => handlePreset(p.key)}
                  >
                    <p className="fw700" style={{ fontSize: 15, marginBottom: 4 }}>
                      {p.label}
                    </p>
                    <p className="muted-sm">{p.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
          )
        )}

        {/* ═══════ SCREENER ═══════ */}
        {page === "screener" && (
          <div className="page-col">
            <div className="search-row">
              <input
                className="search-input"
                style={{ flex: 1 }}
                placeholder="Try: 'Show me momentum tech stocks…'"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              />
              <button className="btn btn-primary" onClick={handleSearch} disabled={searching}>
                {searching ? "…" : "Search"}
              </button>
            </div>

            {aiAnswer && (
              <div className="ai-bubble">
                {aiAnswer}
              </div>
            )}

            {searching && <ScreenerSkeleton />}

            {!searching && results.length === 0 && (
              <div className="center-empty">
                <p>No results yet... try a search above.</p>
              </div>
            )}

            {!searching && results.length > 0 && (
              <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                <div className="table-header-bar">
                  <span className="fw600">{results.length} results</span>
                </div>
                <div style={{ padding: "0 24px" }}>
                  {/* Column headers */}
                  <div className="table-cols">
                    <div className="col-label" style={{ flex: 1.825, textAlign: "left" }}>Stock</div>
                    <div className="col-label" style={{ flex: 1, textAlign: "right" }}>RSI</div>
                    <div className="col-label" style={{ flex: 1, textAlign: "right" }}>20d Ret</div>
                    <div className="col-label" style={{ flex: 1, textAlign: "right" }}>P/E</div>
                    <div className="col-label" style={{ flex: 1, textAlign: "right" }}>Mkt Cap</div>
                    <div style={{ width: 40 }} />
                  </div>
                  {results.map((s) => (
                    <div
                      key={s.ticker}
                      className="stock-row"
                      onClick={() => openStock(s.ticker)}
                    >
                      {/* <div className="ticker-badge">{s.ticker?.slice(0, 3)}</div> */}
                      <div style={{ flex: 2 }}>
                        <p className="fw700" style={{ fontSize: 15 }}>{s.ticker}</p>
                        <p className="muted-sm">{s.sector || ""}</p>
                      </div>
                      <div style={{ flex: 1, textAlign: "right" }}>
                        <span
                          className="badge"
                          style={{
                            background:
                              s.rsi_14 > 65
                                ? "#fef2f2"
                                : s.rsi_14 < 40
                                ? "#eff6ff"
                                : "#f0fdf4",
                            color:
                              s.rsi_14 > 65
                                ? "#ef4444"
                                : s.rsi_14 < 40
                                ? "#3b82f6"
                                : "#22c55e",
                          }}
                        >
                          {s.rsi_14 != null ? s.rsi_14.toFixed(1) : "—"}
                        </span>
                      </div>
                      <div style={{ flex: 1, textAlign: "right" }}>
                        <span className={s.ret_20d >= 0 ? "clr-green fw600" : "clr-red fw600"}>
                          {fmtPct(s.ret_20d)}
                        </span>
                      </div>
                      <div style={{ flex: 1, textAlign: "right", color: "#555", fontSize: 14 }}>
                        {s.trailing_pe != null ? `${s.trailing_pe.toFixed(1)}x` : "—"}
                      </div>
                      <div style={{ flex: 1, textAlign: "right", color: "#555", fontSize: 14 }}>
                        {fmtCap(s.market_cap)}
                      </div>
                      <button
                        className="watch-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleWatchlist(s.ticker);
                        }}
                      >
                        {watchlist.includes(s.ticker) ? "⭐" : "☆"}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ═══════ STOCK DETAIL ═══════ */}
        {page === "detail" && (
          <div className="page-col">
            <button
              className="btn btn-secondary"
              onClick={() => setPage("screener")}
              style={{ width: "fit-content", padding: "8px 16px", fontSize: 14 }}
            >
              ← Back to results
            </button>

            {detailLoading && (
              <DetailSkeleton />
            )}

            {!detailLoading && detail && (() => {
              const prices = detail.price_history || [];
              const indicators = detail.indicator_history || [];
              const fund = detail.fundamentals || {};
              const lastPrice = prices.length > 0 ? prices[prices.length - 1] : null;
              const prevPrice = prices.length > 1 ? prices[prices.length - 2] : null;
              const lastInd = indicators.length > 0 ? indicators[indicators.length - 1] : {};
              const change1d = lastPrice && prevPrice
                ? ((lastPrice.close - prevPrice.close) / prevPrice.close)
                : lastInd.ret_1d ?? null;

              const chartData = prices.map((p, i) => ({
                date: p.date,
                close: p.close,
                sma20: indicators[i]?.sma_20 ?? null,
              }));

              return (
                <>
                  {/* Header card */}
                  <div className="card">
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                          <span className="detail-ticker">{detail.ticker}</span>
                          {fund.sector && (
                            <span className="badge" style={{ background: "#f0f0f8", color: "#6c63ff", fontSize: 13 }}>
                              {fund.sector}
                            </span>
                          )}
                        </div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        {lastPrice && (
                          <>
                            <p className="detail-price">${lastPrice.close.toFixed(2)}</p>
                            <p className={change1d >= 0 ? "clr-green fw600" : "clr-red fw600"} style={{ fontSize: 16 }}>
                              {change1d >= 0 ? "▲" : "▼"} {fmtPct(change1d)} today
                            </p>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Chart */}
                  <div className="card">
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                      <h3 className="fw700">Price Chart</h3>
                      <div style={{ display: "flex", gap: 4 }}>
                        {["1W", "1M", "3M", "1Y"].map((t) => (
                          <span
                            key={t}
                            className={`period-btn ${detailPeriod === t ? "active" : ""}`}
                            onClick={() => openStock(detail.ticker, t)}
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                    {chartData.length > 0 ? (
                      <ResponsiveContainer width="100%" height={200}>
                        <AreaChart data={chartData}>
                          <defs>
                            <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#6c63ff" stopOpacity={0.25} />
                              <stop offset="100%" stopColor="#6c63ff" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f4" />
                          <XAxis
                            dataKey="date"
                            tick={{ fontSize: 11, fill: "#999" }}
                            tickFormatter={(v) => {
                              const d = new Date(v);
                              return `${d.getMonth() + 1}/${d.getDate()}`;
                            }}
                            minTickGap={30}
                          />
                          <YAxis
                            domain={["auto", "auto"]}
                            tick={{ fontSize: 11, fill: "#999" }}
                            tickFormatter={(v) => `$${v.toFixed(0)}`}
                            width={55}
                          />
                          <Tooltip
                            contentStyle={{ borderRadius: 10, border: "1px solid #e8e8f0", fontSize: 13 }}
                            formatter={(v) => [`$${Number(v).toFixed(2)}`, ""]}
                            labelFormatter={(l) => fmtDate(l)}
                          />
                          <Area
                            type="monotone"
                            dataKey="close"
                            stroke="#6c63ff"
                            strokeWidth={2}
                            fill="url(#grad)"
                            name="Close"
                          />
                          <Area
                            type="monotone"
                            dataKey="sma20"
                            stroke="#a78bfa"
                            strokeWidth={1.5}
                            strokeDasharray="4 3"
                            fill="none"
                            name="SMA 20"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="center-empty" style={{ padding: 40 }}>
                        No chart data
                      </div>
                    )}
                  </div>

                  {/* Stats grid */}
                  <div className="stats-grid">
                    {[
                      {
                        label: "RSI (14)",
                        value: lastInd.rsi_14 != null ? lastInd.rsi_14.toFixed(1) : "—",
                        note:
                          lastInd.rsi_14 > 65
                            ? "Overbought"
                            : lastInd.rsi_14 < 40
                            ? "Oversold"
                            : "Neutral",
                      },
                      {
                        label: "P/E Ratio",
                        value: fund.trailing_pe != null ? `${fund.trailing_pe.toFixed(1)}x` : "—",
                        note: "Trailing",
                      },
                      {
                        label: "Market Cap",
                        value: fmtCap(fund.market_cap),
                        note: "USD",
                      },
                      {
                        label: "20d Return",
                        value: lastInd.ret_20d != null ? fmtPct(lastInd.ret_20d) : "—",
                        note: "Momentum",
                      },
                      {
                        label: "MACD",
                        value: lastInd.macd != null ? lastInd.macd.toFixed(2) : "—",
                        note: lastInd.macd_hist > 0 ? "Bullish" : lastInd.macd_hist < 0 ? "Bearish" : "—",
                      },
                      {
                        label: "Avg Volume",
                        value: fund.avg_volume != null ? (fund.avg_volume / 1e6).toFixed(1) + "M" : "—",
                        note: "Daily",
                      },
                      {
                        label: "SMA 20",
                        value: lastInd.sma_20 != null ? `$${lastInd.sma_20.toFixed(2)}` : "—",
                        note: lastPrice && lastInd.sma_20 ? (lastPrice.close > lastInd.sma_20 ? "Above" : "Below") : "",
                      },
                      {
                        label: "SMA 50",
                        value: lastInd.sma_50 != null ? `$${lastInd.sma_50.toFixed(2)}` : "—",
                        note: lastPrice && lastInd.sma_50 ? (lastPrice.close > lastInd.sma_50 ? "Above" : "Below") : "",
                      },
                    ].map((s) => (
                      <div key={s.label} className="stat-box">
                        <p className="stat-label">{s.label}</p>
                        <p className="stat-value">{s.value}</p>
                        <p className="stat-note">{s.note}</p>
                      </div>
                    ))}
                  </div>

                  {/* Watchlist toggle */}
                  <button
                    className="btn"
                    onClick={() => toggleWatchlist(detail.ticker)}
                    style={{
                      background: watchlist.includes(detail.ticker) ? "#fef2f2" : "#f0fdf4",
                      color: watchlist.includes(detail.ticker) ? "#ef4444" : "#22c55e",
                      width: "fit-content",
                    }}
                  >
                    {watchlist.includes(detail.ticker)
                      ? "★ Remove from Watchlist"
                      : "☆ Add to Watchlist"}
                  </button>
                </>
              );
            })()}
          </div>
        )}

        {/* ═══════ WATCHLIST ═══════ */}
        {page === "watchlist" && (
          <div className="page-col">
            {watchlistLoading ? (
              <WatchlistSkeleton />
            ) : (
              <>
            <h1 className="section-title" style={{ fontSize: 24 }}>
              Your Watchlist
            </h1>
            {watchlist.length === 0 ? (
              <div className="card center-empty" style={{ padding: 48 }}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>☆</div>
                <p style={{ fontSize: 16, marginBottom: 8 }}>No stocks saved yet</p>
                <p className="muted-sm">Star any stock from the screener to add it here</p>
              </div>
            ) : (
              <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                <div style={{ padding: "0 24px" }}>
                  {watchlist.map((ticker) => (
                    <div
                      key={ticker}
                      className="stock-row"
                      onClick={() => openStock(ticker)}
                    >
                      <div className="ticker-badge">{ticker.slice(0, 3)}</div>
                      <div style={{ flex: 2 }}>
                        <p className="fw700" style={{ fontSize: 15 }}>{ticker}</p>
                      </div>
                      <button
                        className="watch-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleWatchlist(ticker);
                        }}
                      >
                        ⭐
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
              </>
            )}
          </div>
        )}
      </div>
      <footer className="site-footer">
        <div className="container">
          <small style={{ color: '#888' }}>MIT License · 2026 Edris Adel</small>
        </div>
      </footer>
    </div>
  );
}
