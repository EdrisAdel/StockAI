alter table if exists fundamentals_daily
  add column if not exists sector text;

alter table if exists indicators_daily
  add column if not exists macd numeric(18,8),
  add column if not exists macd_signal numeric(18,8),
  add column if not exists macd_hist numeric(18,8);
