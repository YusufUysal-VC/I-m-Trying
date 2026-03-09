#!/usr/bin/env python3
"""
analyze.py — Main entry point for Market Analyzer.
Orchestrates data fetching, indicator computation, narrative generation,
and HTML report production.

Usage:
  python analyze.py                          # All instruments
  python analyze.py --ai                     # With AI analysis
  python analyze.py --category "Kripto Para" # Single category
  python analyze.py --symbol THYAO.IS        # Single symbol
  python analyze.py --output ./my_report.html
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Load .env before any other imports
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add project root to path so src.* imports work
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_fetcher import fetch_all_timeframes, load_watchlist, get_current_price, get_price_change_pct
from src.indicators import compute_all_indicators
from src.trend_analyzer import compute_trend_score, compute_instrument_analysis
from src.narrative_engine import generate_narratives
from src.report_writer import generate_commentary, generate_card_summary
from src.chart_builder import build_chart
from src.report_template import render_report

# ─────────────────────────── Logging setup ──────────────────

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def setup_logging(verbose: bool = False) -> None:
    log_file = LOG_DIR / f"analyze_{datetime.now().strftime('%Y%m%d')}.log"
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


logger = logging.getLogger(__name__)


# ─────────────────────────── Core processing ────────────────


def process_symbol(
    symbol: str,
    display_name: str,
    category: str,
    currency: str,
    use_ai: bool = False,
) -> dict:
    """
    Full pipeline for one instrument:
    1. Fetch OHLCV for all timeframes
    2. Compute indicators per timeframe
    3. Compute trend scores
    4. Generate narratives & action plans
    5. Build charts
    6. Generate commentary
    Returns instrument data dict for the report.
    """
    logger.info(f"Processing {symbol}...")

    # Step 1: Fetch data
    all_data = fetch_all_timeframes(symbol)
    if not any(v is not None for v in all_data.values()):
        logger.warning(f"No data available for {symbol}")
        return _empty_instrument(symbol, display_name, category)

    # Step 2: Current price & change
    current_price = 0.0
    change_pct = None
    for tf_label in ["Günlük", "Haftalık"]:
        df = all_data.get(tf_label)
        if df is not None and not df.empty:
            current_price = float(df["Close"].iloc[-1])
            if len(df) >= 2:
                prev = float(df["Close"].iloc[-2])
                if prev > 0:
                    change_pct = round((current_price - prev) / prev * 100, 2)
            break

    # Step 3: Compute indicators per timeframe
    all_indicators = {}
    for tf_label, df in all_data.items():
        if df is not None:
            ind = compute_all_indicators(symbol, tf_label, df)
            all_indicators[tf_label] = ind
            logger.debug(f"  {tf_label}: RSI={ind.rsi}, trend={ind.ema_alignment}")

    # Step 4: Compute trend scores & instrument analysis
    analysis = compute_instrument_analysis(
        symbol=symbol,
        display_name=display_name,
        category=category,
        currency=currency,
        all_indicators=all_indicators,
        current_price=current_price,
        price_change_pct=change_pct or 0.0,
    )

    # Step 5: Generate narratives & action plans
    narrative = generate_narratives(analysis)

    # Step 6: AI enrichment (optional)
    if use_ai:
        _apply_ai_enrichment(symbol, analysis, narrative)

    # Step 7: Build charts per timeframe
    timeframe_charts = {}
    timeframe_commentary = {}
    for tf_label, ind in all_indicators.items():
        if ind.df is not None and len(ind.df) >= 5:
            try:
                chart_html = build_chart(
                    df=ind.df,
                    symbol=symbol,
                    timeframe=tf_label,
                    support_levels=ind.support_levels,
                    resistance_levels=ind.resistance_levels,
                )
                timeframe_charts[tf_label] = chart_html
            except Exception as e:
                logger.error(f"Chart build failed for {symbol} {tf_label}: {e}")
                timeframe_charts[tf_label] = "<div class='chart-unavailable'>Grafik oluşturulamadı.</div>"

        # Step 8: Generate rule-based commentary per timeframe
        trend = analysis.trends.get(tf_label)
        if trend:
            try:
                commentary = generate_commentary(ind, trend, symbol, tf_label)
                timeframe_commentary[tf_label] = commentary
            except Exception as e:
                logger.error(f"Commentary failed for {symbol} {tf_label}: {e}")

    # Step 9: Card summary (Layer 2)
    card_summary = generate_card_summary(analysis, narrative)

    # Get primary timeframe RSI
    primary_ind = all_indicators.get("Günlük") or all_indicators.get("Haftalık")
    primary_rsi = primary_ind.rsi if primary_ind else None

    # Best R:R
    active_plan = narrative.long_plan if narrative.dominant_direction == "LONG" else narrative.short_plan
    rr_t1 = active_plan.risk_reward_t1 if (active_plan and active_plan.is_valid) else None

    return {
        "symbol": symbol,
        "display_name": display_name,
        "category": category,
        "currency": currency,
        "price": current_price,
        "current_price": current_price,
        "change_pct": change_pct,
        "action_status": narrative.action_status,
        "overall_trend": analysis.overall_trend,
        "rsi": primary_rsi,
        "rr_t1": rr_t1,
        "narrative": narrative,
        "card_summary": card_summary,
        "timeframe_charts": timeframe_charts,
        "timeframe_commentary": timeframe_commentary,
        "opportunity_score": narrative.opportunity_score,
        "_analysis": analysis,
    }


def _apply_ai_enrichment(symbol, analysis, narrative):
    """Apply Claude AI enrichment to narrative if API is available."""
    try:
        from src.ai_analyst import get_ai_narrative, build_indicator_dict
        daily_ind = analysis.indicators.get("Günlük")
        if daily_ind is None:
            return
        long_plan = narrative.long_plan
        short_plan = narrative.short_plan

        long_summary = ""
        if long_plan and long_plan.is_valid:
            long_summary = (
                f"Giriş {long_plan.entry_zone_low}-{long_plan.entry_zone_high}, "
                f"Hedef {long_plan.target_1}, Stop {long_plan.stop_loss}"
            )

        short_summary = ""
        if short_plan and short_plan.is_valid:
            short_summary = (
                f"Giriş {short_plan.entry_zone_low}-{short_plan.entry_zone_high}, "
                f"Stop {short_plan.stop_loss}"
            )

        ai_text = get_ai_narrative(
            symbol=symbol,
            short_narrative=narrative.short_narrative,
            long_narrative=narrative.long_narrative,
            long_plan_summary=long_summary,
            short_plan_summary=short_summary,
        )
        if ai_text:
            narrative.short_narrative = ai_text
    except Exception as e:
        logger.error(f"AI enrichment failed for {symbol}: {e}")


def _empty_instrument(symbol: str, display_name: str, category: str) -> dict:
    """Return a placeholder for instruments with no data."""
    return {
        "symbol": symbol,
        "display_name": display_name,
        "category": category,
        "currency": "",
        "price": 0.0,
        "current_price": 0.0,
        "change_pct": None,
        "action_status": "Nötr",
        "overall_trend": "Yatay",
        "rsi": None,
        "rr_t1": None,
        "narrative": None,
        "card_summary": {"action_status": "Nötr", "action_reason": "Veri alınamadı", "scenario_branches": []},
        "timeframe_charts": {},
        "timeframe_commentary": {},
        "opportunity_score": 0.0,
        "_error": "Veri alınamadı",
    }


# ─────────────────────────── Report assembly ────────────────


def select_opportunities(all_instruments: list, top_n: int = 5) -> list:
    """Select top N opportunities sorted by opportunity score."""
    actionable = [i for i in all_instruments if i.get("action_status") in ("Al", "Sat", "İzle")]
    sorted_insts = sorted(actionable, key=lambda x: x.get("opportunity_score", 0), reverse=True)
    result = []
    for inst in sorted_insts[:top_n]:
        plan = None
        narr = inst.get("narrative")
        if narr:
            plan = narr.long_plan if narr.dominant_direction == "LONG" else narr.short_plan

        rr_text = ""
        reason = inst.get("card_summary", {}).get("action_reason", "")
        if plan and plan.is_valid and plan.risk_reward_t1 > 0:
            rr_text = f"R:R 1:{plan.risk_reward_t1}"

        result.append({
            "symbol": inst["symbol"],
            "display_name": inst.get("display_name", ""),
            "action_status": inst["action_status"],
            "rr_text": rr_text,
            "reason": reason,
        })
    return result


def build_report_data(
    category_results: dict,  # cat_name -> [instrument_dict]
    generated_at: datetime,
) -> dict:
    """Assemble the full report data structure."""
    all_instruments = []
    for instruments in category_results.values():
        all_instruments.extend(instruments)

    opportunities = select_opportunities(all_instruments)

    return {
        "generated_at": generated_at,
        "opportunities": opportunities,
        "all_instruments": all_instruments,
        "categories": category_results,
    }


# ─────────────────────────── CLI ────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="Market Analyzer — Multi-asset technical analysis report generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze.py
  python analyze.py --ai
  python analyze.py --category "Kripto Para"
  python analyze.py --symbol BTC-USD
  python analyze.py --output ./reports/morning.html
        """,
    )
    parser.add_argument("--ai", action="store_true", help="Enable Claude AI analysis (requires ANTHROPIC_API_KEY)")
    parser.add_argument("--category", type=str, default=None, help="Analyze only this category")
    parser.add_argument("--symbol", type=str, default=None, help="Analyze only this symbol")
    parser.add_argument("--output", type=str, default=None, help="Output HTML file path")
    parser.add_argument("--watchlist", type=str, default=None, help="Path to watchlist.json")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args.verbose)
    logger.info("=" * 60)
    logger.info("Market Analyzer starting...")

    if args.ai:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            logger.warning("--ai flag set but ANTHROPIC_API_KEY not found in environment. AI analysis disabled.")
            args.ai = False
        else:
            logger.info("AI analysis enabled (claude-sonnet-4-6)")

    # Load watchlist
    try:
        watchlist = load_watchlist(args.watchlist)
        logger.info(f"Watchlist loaded: {sum(len(v.get('symbols',[])) for v in watchlist['categories'].values())} instruments")
    except Exception as e:
        logger.error(f"Failed to load watchlist: {e}")
        sys.exit(1)

    # Determine what to process
    categories_to_process = watchlist["categories"]
    if args.category:
        if args.category not in categories_to_process:
            logger.error(f"Category '{args.category}' not found. Available: {list(categories_to_process.keys())}")
            sys.exit(1)
        categories_to_process = {args.category: categories_to_process[args.category]}

    if args.symbol:
        # Find which category the symbol belongs to
        found = False
        for cat_name, cat_data in categories_to_process.items():
            if args.symbol in cat_data.get("symbols", []):
                categories_to_process = {cat_name: {"symbols": [args.symbol], **cat_data}}
                found = True
                break
        if not found:
            logger.error(f"Symbol '{args.symbol}' not found in watchlist.")
            sys.exit(1)

    # Process all instruments
    generated_at = datetime.now()
    category_results = {}

    for cat_name, cat_data in categories_to_process.items():
        symbols = cat_data.get("symbols", [])
        display_names = cat_data.get("display_names", {})
        currency = cat_data.get("currency", "USD")
        logger.info(f"\nCategory: {cat_name} ({len(symbols)} symbols)")

        instruments = []
        for symbol in symbols:
            display_name = display_names.get(symbol, symbol.replace(".IS", "").replace("-USD", "").replace("=X", "").replace("=F", ""))
            try:
                inst_data = process_symbol(
                    symbol=symbol,
                    display_name=display_name,
                    category=cat_name,
                    currency=currency,
                    use_ai=args.ai,
                )
                instruments.append(inst_data)
                status = inst_data.get("action_status", "Nötr")
                price = inst_data.get("price", 0)
                logger.info(f"  ✓ {symbol}: {price:.2f} | {status}")
            except Exception as e:
                logger.error(f"  ✗ {symbol}: {e}")
                instruments.append(_empty_instrument(symbol, display_name, cat_name))

        category_results[cat_name] = instruments

    # Build and render report
    logger.info("\nBuilding report...")
    report_data = build_report_data(category_results, generated_at)

    try:
        html_content = render_report(report_data)
    except Exception as e:
        logger.error(f"Report rendering failed: {e}")
        raise

    # Save output
    if args.output:
        output_path = Path(args.output)
    else:
        filename = f"report_{generated_at.strftime('%Y%m%d_%H%M')}.html"
        output_path = OUTPUT_DIR / filename

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")

    logger.info(f"\nReport saved: {output_path}")
    logger.info(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
    logger.info("Done.")

    return str(output_path)


if __name__ == "__main__":
    main()
