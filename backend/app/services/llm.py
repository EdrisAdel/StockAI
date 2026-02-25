import re
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings
from app.schemas import FilterCondition, StockScreenIntent


_SECTOR_KEYWORDS: dict[str, list[str]] = {
    "Technology": ["technology", "tech", "software", "semiconductor", "semiconductors", "chip", "chips"],
    "Communication Services": ["communication", "communications", "telecom", "media", "internet services"],
    "Healthcare": ["healthcare", "health", "biotech", "biotechnology", "pharma", "pharmaceutical", "medical"],
    "Financials": ["financial", "financials", "bank", "banks", "banking", "insurance", "insurer"],
    "Industrials": ["industrial", "industrials", "manufacturing", "aerospace", "defense", "defence"],
    "Energy": ["energy", "oil", "gas", "renewable", "renewables"],
    "Consumer Cyclical": ["consumer cyclical", "cyclical", "discretionary", "retail", "automotive", "auto"],
    "Consumer Defensive": ["consumer defensive", "defensive", "staples", "food", "beverage"],
    "Utilities": ["utilities", "utility"],
    "Real Estate": ["real estate", "reit", "reits"],
    "Basic Materials": ["basic materials", "materials", "mining", "chemical", "chemicals"],
}


def _extract_sector_filters(question: str) -> list[str]:
    q = question.lower()
    matched_sectors: list[str] = []
    for sector, keywords in _SECTOR_KEYWORDS.items():
        if any(keyword in q for keyword in keywords):
            matched_sectors.append(sector)

    if "tech" in q and "Communication Services" not in matched_sectors:
        matched_sectors.append("Communication Services")

    seen: set[str] = set()
    deduped: list[str] = []
    for sector in matched_sectors:
        if sector not in seen:
            seen.add(sector)
            deduped.append(sector)
    return deduped


def _enforce_sector_filters(question: str, intent: StockScreenIntent) -> StockScreenIntent:
    if intent.action != "screen_stocks":
        return intent

    sectors = _extract_sector_filters(question)
    if not sectors:
        return intent

    non_sector_filters = [f for f in intent.filters if f.field != "sector"]
    non_sector_filters.append(FilterCondition(field="sector", op="in", value=sectors))
    intent.filters = non_sector_filters
    return intent


def _heuristic_intent(question: str) -> StockScreenIntent:
    q = question.lower()
    filters: list[FilterCondition] = []
    n = 10

    ticker_match = re.search(r"\b([A-Z]{1,5}(?:-[A-Z])?)\b", question)
    if any(word in q for word in ["snapshot", "quote", "show", "price"]) and ticker_match:
        return StockScreenIntent(action="ticker_snapshot", ticker=ticker_match.group(1), n=1)

    match = re.search(r"top\s+(\d+)", q)
    if match:
        n = max(1, min(100, int(match.group(1))))

    if "undervalued" in q:
        filters.append(FilterCondition(field="forward_pe", op="<", value=30))
    if "tech" in q or "technology" in q:
        filters.append(FilterCondition(field="sector", op="in", value=["Technology", "Communication Services"]))
    if "strong earnings momentum" in q or "momentum" in q:
        filters.append(FilterCondition(field="ret_20d", op=">", value=0.015))
        filters.append(FilterCondition(field="macd_hist", op=">", value=-0.01))
    if "oversold" in q:
        filters.append(FilterCondition(field="rsi_14", op="<", value=30))
    if "overbought" in q:
        filters.append(FilterCondition(field="rsi_14", op=">", value=70))

    # handle negative qualifiers like "low rsi" or "low market cap"
    if "low rsi" in q or "rsi under" in q or "rsi below" in q:
        filters.append(FilterCondition(field="rsi_14", op="<", value=30))
    if "low market cap" in q or "small cap" in q or "market cap low" in q:
        filters.append(FilterCondition(field="market_cap", op="<", value=5000000000))

    intent = StockScreenIntent(action="screen_stocks", filters=filters, sort_by="ret_20d", sort_order="desc", n=n)
    return _enforce_sector_filters(question, intent)


def question_to_intent(question: str) -> StockScreenIntent:
    if not settings.openai_api_key:
        return _enforce_sector_filters(question, _heuristic_intent(question))

    parser = PydanticOutputParser(pydantic_object=StockScreenIntent)
    llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a finance query router. Convert user question into StockScreenIntent. "
                "Use only fields/operators allowed by schema. Never invent tickers or data. "
                "Pay close attention to adjectives such as 'low', 'high', 'under', or 'above' and translate them to the appropriate comparison operator. "
                "For example, 'low rsi' should become rsi_14 < 30, 'high momentum' should add positive ret_20d, etc. "
                "For 'undervalued', prefer trailing_pe or forward_pe thresholds. "
                "For momentum, use ret_20d, macd_hist, or rsi_14 with realistic non-extreme thresholds. "
                "If the request asks for one ticker, use action=ticker_snapshot and set ticker. "
                "For broad thematic requests, prefer action=screen_stocks and include 2-5 filters. "
                "If unsure, use action=screen_stocks with no filters, sort_by=ret_20d, sort_order=desc, n=10.",
            ),
            ("human", "Question: {question}\n{format_instructions}"),
        ]
    )

    chain = prompt | llm | parser
    try:
        intent = chain.invoke({"question": question, "format_instructions": parser.get_format_instructions()})
        return _enforce_sector_filters(question, intent)
    except Exception:  # noqa: BLE001
        return _enforce_sector_filters(question, _heuristic_intent(question))


def build_nl_answer(question: str, intent: StockScreenIntent, result: list[dict[str, Any]]) -> str:
    if not result:
        return "No matching stocks were found in the current database snapshot for your criteria. Try relaxing one or more filters."

    if not settings.openai_api_key:
        tickers = ", ".join([str(r.get("ticker")) for r in result[:5]])
        return f"Found {len(result)} matching stocks. Top matches: {tickers}."

    llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a financial screening assistant. Use ONLY the provided result rows. "
                "Do not invent tickers, metrics, or values. "
                "If results are empty, clearly say no matches were found.",
            ),
            (
                "human",
                "User question: {question}\n"
                "Executed intent: {intent}\n"
                "Screening results: {result}\n\n"
                "Return a concise summary with: "
                "1) match count, 2) top 3 tickers with key metric clues, 3) one suggested next refinement.",
            ),
        ]
    )

    chain = prompt | llm
    try:
        response = chain.invoke({"question": question, "intent": intent.model_dump_json(), "result": result})
        return str(response.content)
    except Exception:  # noqa: BLE001
        tickers = ", ".join([str(r.get("ticker")) for r in result[:5]])
        return f"Found {len(result)} matching stocks. Top matches: {tickers}."
