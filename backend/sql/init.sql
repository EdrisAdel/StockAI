create table if not exists prices_daily (
  ticker text not null,
  trade_date date not null,
  open numeric(18,6) not null,
  high numeric(18,6) not null,
  low numeric(18,6) not null,
  close numeric(18,6) not null,
  adj_close numeric(18,6),
  volume bigint not null,
  source text default 'yfinance',
  updated_at timestamptz default now(),
  primary key (ticker, trade_date)
);

create table if not exists fundamentals_daily (
  ticker text not null,
  as_of_date date not null,
  market_cap numeric(20,2),
  trailing_pe numeric(18,6),
  forward_pe numeric(18,6),
  avg_volume bigint,
  sector text,
  source text default 'yfinance',
  updated_at timestamptz default now(),
  primary key (ticker, as_of_date)
);

create table if not exists indicators_daily (
  ticker text not null,
  trade_date date not null,
  sma_20 numeric(18,6),
  sma_50 numeric(18,6),
  rsi_14 numeric(18,6),
  vol_20 numeric(18,6),
  ret_1d numeric(18,8),
  ret_20d numeric(18,8),
  macd numeric(18,8),
  macd_signal numeric(18,8),
  macd_hist numeric(18,8),
  updated_at timestamptz default now(),
  primary key (ticker, trade_date),
  foreign key (ticker, trade_date) references prices_daily(ticker, trade_date) on delete cascade
);

create table if not exists run_log (
  id bigserial primary key,
  run_at timestamptz default now(),
  status text not null,
  message text
);

create index if not exists idx_prices_date on prices_daily(trade_date);
create index if not exists idx_indicators_date on indicators_daily(trade_date);
