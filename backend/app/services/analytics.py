from datetime import date
from typing import Any

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models import FundamentalDaily, IndicatorDaily, PriceDaily
from app.schemas import FilterCondition, StockScreenIntent


_FIELD_MAP = {
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
    "sector": FundamentalDaily.sector,
}


def _build_predicate(filter_condition: FilterCondition):
    col = _FIELD_MAP[filter_condition.field]
    op = filter_condition.op
    value = filter_condition.value

    if filter_condition.field == "sector":
        if op == "in" and isinstance(value, list):
            normalized = [str(v).strip() for v in value if str(v).strip()]
            return col.in_(normalized)
        if op in {"=", "!="} and isinstance(value, str):
            return col == value.strip() if op == "=" else col != value.strip()
        raise ValueError("sector filter only supports '=', '!=', or 'in' with string values")

    if not isinstance(value, (int, float)):
        raise ValueError(f"{filter_condition.field} requires a numeric value")

    if op == ">":
        return col > value
    if op == ">=":
        return col >= value
    if op == "<":
        return col < value
    if op == "<=":
        return col <= value
    if op == "=":
        return col == value
    if op == "!=":
        return col != value

    raise ValueError(f"Unsupported operator: {op}")


def _filter_to_dict(filter_condition: FilterCondition) -> dict[str, Any]:
    return {
        "field": filter_condition.field,
        "op": filter_condition.op,
        "value": filter_condition.value,
    }


def _latest_fund_date_subquery():
    return (
        select(FundamentalDaily.ticker, func.max(FundamentalDaily.as_of_date).label("max_as_of_date"))
        .group_by(FundamentalDaily.ticker)
        .subquery()
    )


def _field_has_data(db: Session, field: str, latest_indicator_date: date) -> bool:
    col = _FIELD_MAP[field]
    if field in {"rsi_14", "ret_20d", "vol_20", "sma_20", "sma_50", "macd", "macd_signal", "macd_hist"}:
        count_non_null = db.scalar(
            select(func.count())
            .select_from(IndicatorDaily)
            .where(IndicatorDaily.trade_date == latest_indicator_date)
            .where(col.is_not(None))
        )
        return bool(count_non_null and count_non_null > 0)

    latest_fund_date_sq = _latest_fund_date_subquery()
    count_non_null = db.scalar(
        select(func.count())
        .select_from(FundamentalDaily)
        .join(
            latest_fund_date_sq,
            and_(
                FundamentalDaily.ticker == latest_fund_date_sq.c.ticker,
                FundamentalDaily.as_of_date == latest_fund_date_sq.c.max_as_of_date,
            ),
        )
        .where(col.is_not(None))
    )
    return bool(count_non_null and count_non_null > 0)


def _relax_filter(filter_condition: FilterCondition) -> FilterCondition:
    if not isinstance(filter_condition.value, (int, float)):
        return filter_condition

    value = float(filter_condition.value)
    relaxed_value = value

    if filter_condition.op in {">", ">="}:
        relaxed_value = value * 0.85 if value >= 0 else value * 1.15
    elif filter_condition.op in {"<", "<="}:
        relaxed_value = value * 1.15 if value >= 0 else value * 0.85

    return FilterCondition(field=filter_condition.field, op=filter_condition.op, value=relaxed_value)


def _execute_screen_query(db: Session, intent: StockScreenIntent, filters: list[FilterCondition], latest_indicator_date: date):
    latest_fund_date_sq = _latest_fund_date_subquery()
    sort_col = _FIELD_MAP[intent.sort_by]
    order_clause = desc(sort_col) if intent.sort_order == "desc" else asc(sort_col)

    query = (
        select(
            IndicatorDaily.ticker,
            IndicatorDaily.trade_date,
            IndicatorDaily.rsi_14,
            IndicatorDaily.ret_20d,
            IndicatorDaily.vol_20,
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
        .where(IndicatorDaily.trade_date == latest_indicator_date)
    )

    if intent.ticker:
        query = query.where(IndicatorDaily.ticker == intent.ticker.upper())

    predicates = [_build_predicate(f) for f in filters]
    if predicates:
        query = query.where(and_(*predicates))

    query = query.where(or_(sort_col.is_not(None), IndicatorDaily.ret_20d.is_not(None))).order_by(order_clause).limit(intent.n)
    return db.execute(query).all()


def top_n_by_metric(db: Session, metric: str, n: int, target_date: date | None):
    if target_date is None:
        target_date = db.scalar(select(func.max(IndicatorDaily.trade_date)))
    if target_date is None:
        return []

    metric_col = getattr(IndicatorDaily, metric)
    q = (
        select(IndicatorDaily.ticker, IndicatorDaily.trade_date, metric_col)
        .where(IndicatorDaily.trade_date == target_date)
        .where(metric_col.is_not(None))
        .order_by(desc(metric_col))
        .limit(n)
    )
    rows = db.execute(q).all()
    return [{"ticker": r[0], "date": r[1], metric: r[2]} for r in rows]


def ticker_snapshot(db: Session, ticker: str):
    latest = db.scalar(select(func.max(PriceDaily.trade_date)).where(PriceDaily.ticker == ticker))
    if latest is None:
        return None

    price = db.execute(
        select(PriceDaily).where(PriceDaily.ticker == ticker, PriceDaily.trade_date == latest)
    ).scalar_one_or_none()
    ind = db.execute(
        select(IndicatorDaily).where(IndicatorDaily.ticker == ticker, IndicatorDaily.trade_date == latest)
    ).scalar_one_or_none()
    if price is None:
        return None

    return {
        "ticker": ticker,
        "date": latest,
        "close": float(price.close),
        "volume": int(price.volume),
        "indicators": {
            "sma_20": float(ind.sma_20) if ind and ind.sma_20 is not None else None,
            "sma_50": float(ind.sma_50) if ind and ind.sma_50 is not None else None,
            "rsi_14": float(ind.rsi_14) if ind and ind.rsi_14 is not None else None,
            "vol_20": float(ind.vol_20) if ind and ind.vol_20 is not None else None,
            "ret_20d": float(ind.ret_20d) if ind and ind.ret_20d is not None else None,
            "macd": float(ind.macd) if ind and ind.macd is not None else None,
            "macd_signal": float(ind.macd_signal) if ind and ind.macd_signal is not None else None,
            "macd_hist": float(ind.macd_hist) if ind and ind.macd_hist is not None else None,
        },
    }


def execute_stock_screen(db: Session, intent: StockScreenIntent):
    latest_indicator_date = intent.date or db.scalar(select(func.max(IndicatorDaily.trade_date)))
    if latest_indicator_date is None:
        return {
            "rows": [],
            "execution": {
                "applied_filters": [],
                "dropped_filters": [],
                "relaxation_steps": [],
                "latest_indicator_date": None,
            },
        }

    applied_filters: list[FilterCondition] = []
    dropped_filters: list[dict[str, Any]] = []
    for f in intent.filters:
        if _field_has_data(db, f.field, latest_indicator_date):
            applied_filters.append(f)
        else:
            dropped_filters.append({
                **_filter_to_dict(f),
                "reason": "field_has_no_data_in_current_snapshot",
            })

    rows = _execute_screen_query(db, intent, applied_filters, latest_indicator_date)
    relaxation_steps: list[dict[str, Any]] = []

    if not rows and applied_filters:
        relaxed_filters = applied_filters
        for round_num in [1, 2]:
            relaxed_filters = [_relax_filter(f) for f in relaxed_filters]
            rows = _execute_screen_query(db, intent, relaxed_filters, latest_indicator_date)
            relaxation_steps.append(
                {
                    "type": "threshold_relaxation",
                    "round": round_num,
                    "filters": [_filter_to_dict(f) for f in relaxed_filters],
                    "rows": len(rows),
                }
            )
            if rows:
                applied_filters = relaxed_filters
                break

        if not rows and len(relaxed_filters) > 1:
            drop_priority = ["macd_hist", "rsi_14", "ret_20d", "trailing_pe", "forward_pe"]
            current = relaxed_filters
            for field_name in drop_priority:
                removable = [f for f in current if f.field == field_name]
                if not removable:
                    continue
                current = [f for f in current if f.field != field_name]
                rows = _execute_screen_query(db, intent, current, latest_indicator_date)
                relaxation_steps.append(
                    {
                        "type": "drop_filter",
                        "field": field_name,
                        "remaining_filters": [_filter_to_dict(f) for f in current],
                        "rows": len(rows),
                    }
                )
                if rows:
                    dropped_filters.append({"field": field_name, "reason": "relaxed_for_non_empty_result_set"})
                    applied_filters = current
                    break

    result = []
    for row in rows:
        result.append(
            {
                "ticker": row.ticker,
                "date": row.trade_date,
                "rsi_14": float(row.rsi_14) if row.rsi_14 is not None else None,
                "ret_20d": float(row.ret_20d) if row.ret_20d is not None else None,
                "vol_20": float(row.vol_20) if row.vol_20 is not None else None,
                "macd": float(row.macd) if row.macd is not None else None,
                "macd_signal": float(row.macd_signal) if row.macd_signal is not None else None,
                "macd_hist": float(row.macd_hist) if row.macd_hist is not None else None,
                "trailing_pe": float(row.trailing_pe) if row.trailing_pe is not None else None,
                "forward_pe": float(row.forward_pe) if row.forward_pe is not None else None,
                "market_cap": float(row.market_cap) if row.market_cap is not None else None,
                "avg_volume": int(row.avg_volume) if row.avg_volume is not None else None,
                "sector": row.sector,
            }
        )
    return {
        "rows": result,
        "execution": {
            "applied_filters": [_filter_to_dict(f) for f in applied_filters],
            "dropped_filters": dropped_filters,
            "relaxation_steps": relaxation_steps,
            "latest_indicator_date": latest_indicator_date,
        },
    }
