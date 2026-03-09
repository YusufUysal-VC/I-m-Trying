#!/usr/bin/env python3
"""
Market Analyzer — Main CLI entry point.
Orchestrates data fetching, indicator computation, analysis, and report generation.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.data_fetcher import load_watchlist, fetch_ohlcv, TIMEFRAMES
from src.indicators import compute_all_indicators
from src.trend_analyzer import compute_trend_score, compute_timeframe_alignment, get_trend_emoji, get_trend_color
from src.narrative_engine import generate_narrative, score_opportunity
from src.report_writer import generate_commentary
from src.ai_analyst import get_ai_analysis, get_ai_narrative, is_ai_available
from src.chart_builder import build_chart
from src.report_template import (
    render_report, format_price, format_change,
    get_status_order, get_badge_class,
)

# Load .env
load_dotenv(BASE_DIR / ".env")


def setup_logging():
    """Configure logging to file and console."""
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"analyze_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def get_display_name(symbol: str, category_config: dict) -> str:
    """Get a human-readable display name for a symbol."""
    display_names = category_config.get("display_names", {})
    if symbol in display_names:
        return display_names[symbol]
    # Clean up symbol for display
    name = symbol.replace(".IS", "").replace("-USD", "").replace("=X", "").replace("=F", "")
    return name


def analyze_symbol(symbol: str, category_config: dict, use_ai: bool = False) -> dict | None:
    """
    Analyze a single symbol across all timeframes.
    Returns a structured dict ready for report rendering.
    """
    logger = logging.getLogger(__name__)
    display_name = get_display_name(symbol, category_config)
    currency = category_config.get("currency", "USD")
    if currency == "mixed":
        currency = "USD"

    logger.info(f"Analyzing {symbol} ({display_name})")

    import time

    # Fetch data and compute for all timeframes
    timeframe_data = {}
    all_indicators = {}
    all_trends = {}
    primary_indicators = None
    primary_trend = None

    for tf_name, tf_config in TIMEFRAMES.items():
        logger.info(f"  {tf_name}...")
        df = fetch_ohlcv(symbol, tf_name)
        time.sleep(0.5)

        if df is None or df.empty:
            logger.warning(f"  No data for {symbol} [{tf_name}]")
            timeframe_data[tf_name] = {
                "chart_html": f'<div class="chart-error">Veri alınamadı: {symbol} [{tf_name}]</div>',
                "short_narrative": "Veri yetersiz",
                "short_confidence": "Düşük",
                "long_narrative": "Veri yetersiz",
                "long_confidence": "Düşük",
                "commentary": "",
                "ai_analysis": "",
            }
            continue

        # Compute indicators
        indicators = compute_all_indicators(df)
        if indicators is None:
            timeframe_data[tf_name] = {
                "chart_html": f'<div class="chart-error">Göstergeler hesaplanamadı: {symbol} [{tf_name}]</div>',
                "short_narrative": "Veri yetersiz",
                "short_confidence": "Düşük",
                "long_narrative": "Veri yetersiz",
                "long_confidence": "Düşük",
                "commentary": "",
                "ai_analysis": "",
            }
            continue

        all_indicators[tf_name] = indicators

        # Compute trend
        trend = compute_trend_score(indicators, df)
        all_trends[tf_name] = trend

        # Use "Günlük" as primary, or first available
        if tf_name == "Günlük" or primary_indicators is None:
            primary_indicators = indicators
            primary_trend = trend

        # Build chart
        chart_html = build_chart(df, symbol, tf_name, indicators)

        # Compute narrative for this timeframe
        alignment = compute_timeframe_alignment(all_trends) if all_trends else None
        narrative = generate_narrative(indicators, trend, alignment)

        # Generate commentary
        commentary = generate_commentary(symbol, tf_name, indicators, trend, narrative)

        # AI analysis (optional)
        ai_analysis = ""
        if use_ai:
            indicator_summary = {
                "price": indicators.current_price,
                "rsi": indicators.rsi,
                "macd_line": indicators.macd_line,
                "macd_signal": indicators.macd_signal,
                "macd_histogram": indicators.macd_histogram,
                "bb_percent": indicators.bb_percent,
                "bb_squeeze": indicators.bb_squeeze,
                "ema20": indicators.ema20,
                "ema50": indicators.ema50,
                "ema200": indicators.ema200,
                "trend_score": trend.score,
                "trend_label": trend.label,
                "support_levels": [s.price for s in indicators.support_levels],
                "resistance_levels": [r.price for r in indicators.resistance_levels],
            }
            ai_result = get_ai_analysis(symbol, tf_name, indicator_summary)
            if ai_result:
                ai_analysis = ai_result

        timeframe_data[tf_name] = {
            "chart_html": chart_html,
            "short_narrative": narrative.short_term_narrative,
            "short_confidence": narrative.short_term_confidence,
            "long_narrative": narrative.long_term_narrative,
            "long_confidence": narrative.long_term_confidence,
            "commentary": commentary,
            "ai_analysis": ai_analysis,
        }

    if primary_indicators is None:
        logger.warning(f"No usable data for {symbol}")
        return None

    # Final narrative from primary timeframe
    alignment = compute_timeframe_alignment(all_trends) if all_trends else None
    narrative = generate_narrative(primary_indicators, primary_trend, alignment)

    # Format price and change
    price_str = format_price(primary_indicators.current_price, currency)
    change_str, change_class = format_change(primary_indicators.price_change_pct)
    rsi_str = f"{primary_indicators.rsi:.0f}" if primary_indicators.rsi is not None else "—"

    # R:R for dominant direction
    if narrative.dominant_direction == "LONG":
        rr_val = narrative.long_plan.risk_reward_t1
    else:
        rr_val = narrative.short_plan.risk_reward_t1
    rr_str = f"1:{rr_val}" if rr_val > 0 else "—"

    return {
        "symbol": symbol,
        "display_name": display_name,
        "currency": currency,
        "price_str": price_str,
        "change_str": change_str,
        "change_class": change_class,
        "rsi_str": rsi_str,
        "rr_str": rr_str,
        "trend_label": primary_trend.label if primary_trend else "—",
        "trend_color": get_trend_color(primary_trend.label) if primary_trend else "#636e72",
        "action_status": narrative.action_status,
        "action_badge": narrative.action_badge,
        "action_color": narrative.action_color,
        "summary_line": narrative.summary_line,
        "scenario_tree": [
            {
                "icon": b.icon,
                "condition": b.condition,
                "action": b.action,
                "target": b.target,
                "time_horizon": b.time_horizon,
            }
            for b in narrative.scenario_tree
        ],
        "dominant": narrative.dominant_direction,
        "long_plan": {
            "bias_strength": narrative.long_plan.bias_strength,
            "entry_zone_low": f"{narrative.long_plan.entry_zone_low:.4g}",
            "entry_zone_high": f"{narrative.long_plan.entry_zone_high:.4g}",
            "entry_reasoning": narrative.long_plan.entry_reasoning,
            "target_1": f"{narrative.long_plan.target_1:.4g}",
            "target_2": f"{narrative.long_plan.target_2:.4g}",
            "target_3": f"{narrative.long_plan.target_3:.4g}",
            "risk_reward_t1": narrative.long_plan.risk_reward_t1,
            "risk_reward_t2": narrative.long_plan.risk_reward_t2,
            "risk_reward_t3": narrative.long_plan.risk_reward_t3,
            "stop_loss": f"{narrative.long_plan.stop_loss:.4g}",
            "stop_reasoning": narrative.long_plan.stop_reasoning,
            "entry_trigger": narrative.long_plan.entry_trigger,
            "invalidation": narrative.long_plan.invalidation,
            "time_horizon": narrative.long_plan.time_horizon,
            "quality_warning": narrative.long_plan.quality_warning,
        },
        "short_plan": {
            "bias_strength": narrative.short_plan.bias_strength,
            "entry_zone_low": f"{narrative.short_plan.entry_zone_low:.4g}",
            "entry_zone_high": f"{narrative.short_plan.entry_zone_high:.4g}",
            "entry_reasoning": narrative.short_plan.entry_reasoning,
            "target_1": f"{narrative.short_plan.target_1:.4g}",
            "target_2": f"{narrative.short_plan.target_2:.4g}",
            "target_3": f"{narrative.short_plan.target_3:.4g}",
            "risk_reward_t1": narrative.short_plan.risk_reward_t1,
            "risk_reward_t2": narrative.short_plan.risk_reward_t2,
            "risk_reward_t3": narrative.short_plan.risk_reward_t3,
            "stop_loss": f"{narrative.short_plan.stop_loss:.4g}",
            "stop_reasoning": narrative.short_plan.stop_reasoning,
            "entry_trigger": narrative.short_plan.entry_trigger,
            "invalidation": narrative.short_plan.invalidation,
            "time_horizon": narrative.short_plan.time_horizon,
            "quality_warning": narrative.short_plan.quality_warning,
        },
        "timeframes": list(TIMEFRAMES.keys()),
        "timeframe_data": timeframe_data,
        "opportunity_score": narrative.opportunity_score,
        "narrative": narrative,  # Keep for opportunity scoring
    }


def build_report_data(categories_results: dict, report_date: str) -> dict:
    """Build the final report data structure for template rendering."""

    # Summary table
    summary_table = []
    all_instruments = []

    for cat_name, instruments in categories_results.items():
        for inst in instruments:
            if inst is None:
                continue
            all_instruments.append(inst)
            summary_table.append({
                "symbol": inst["symbol"],
                "display_name": inst["display_name"],
                "price_str": inst["price_str"],
                "change_str": inst["change_str"],
                "change_class": inst["change_class"],
                "badge": inst["action_badge"],
                "badge_class": get_badge_class(inst["action_status"]),
                "trend_label": inst["trend_label"],
                "rsi_str": inst["rsi_str"],
                "rr_str": inst["rr_str"],
                "status_order": get_status_order(inst["action_status"]),
            })

    # Sort summary by status order
    summary_table.sort(key=lambda x: x["status_order"])

    # Günün Fırsatları — top 5 by opportunity score
    scored = [(inst, inst["opportunity_score"]) for inst in all_instruments]
    scored.sort(key=lambda x: -x[1])
    opportunities = []
    for inst, score in scored[:5]:
        if score <= 0:
            continue
        narrative = inst["narrative"]
        dominant_plan = narrative.long_plan if narrative.dominant_direction == "LONG" else narrative.short_plan
        rr = dominant_plan.risk_reward_t1

        opportunities.append({
            "symbol": inst["symbol"],
            "display_name": inst["display_name"],
            "badge": inst["action_badge"],
            "color": inst["action_color"],
            "rr": rr,
            "reason": inst["summary_line"],
        })

    # Clean up instrument data (remove non-serializable narrative object)
    clean_categories = {}
    for cat_name, instruments in categories_results.items():
        clean_list = []
        for inst in instruments:
            if inst is None:
                continue
            inst_copy = {k: v for k, v in inst.items() if k != "narrative"}
            clean_list.append(inst_copy)
        clean_categories[cat_name] = clean_list

    return {
        "report_date": report_date,
        "categories": clean_categories,
        "opportunities": opportunities,
        "summary_table": summary_table,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Market Analyzer — Multi-asset technical analysis tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ai", action="store_true", help="Enable Claude AI analysis (requires ANTHROPIC_API_KEY)")
    parser.add_argument("--category", type=str, help="Analyze only a specific category")
    parser.add_argument("--symbol", type=str, help="Analyze only a specific symbol")
    parser.add_argument("--output", type=str, help="Output file path")
    parser.add_argument("--watchlist", type=str, help="Path to watchlist JSON file")
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Market Analyzer starting")
    logger.info("=" * 60)

    # Check AI availability
    if args.ai:
        if is_ai_available():
            logger.info("AI analysis enabled (Claude API)")
        else:
            logger.warning("--ai flag set but ANTHROPIC_API_KEY not found. AI analysis disabled.")
            args.ai = False

    # Load watchlist
    try:
        watchlist = load_watchlist(args.watchlist)
    except Exception as e:
        logger.error(f"Failed to load watchlist: {e}")
        sys.exit(1)

    categories = watchlist.get("categories", {})

    # Filter by category if specified
    if args.category:
        matching = {k: v for k, v in categories.items() if args.category.lower() in k.lower()}
        if not matching:
            logger.error(f"Category not found: {args.category}")
            logger.info(f"Available categories: {', '.join(categories.keys())}")
            sys.exit(1)
        categories = matching

    # Analyze
    categories_results = {}

    for cat_name, cat_config in categories.items():
        symbols = cat_config.get("symbols", [])

        # Filter by symbol if specified
        if args.symbol:
            symbols = [s for s in symbols if s == args.symbol]
            if not symbols:
                continue

        logger.info(f"\n{'='*40}")
        logger.info(f"Category: {cat_name}")
        logger.info(f"{'='*40}")

        instruments = []
        for symbol in symbols:
            try:
                result = analyze_symbol(symbol, cat_config, use_ai=args.ai)
                instruments.append(result)
            except Exception as e:
                logger.error(f"Failed to analyze {symbol}: {e}", exc_info=True)
                instruments.append(None)

        categories_results[cat_name] = instruments

    # Build report
    report_date = datetime.now().strftime("%d %b %Y, %H:%M")
    report_data = build_report_data(categories_results, report_date)

    # Render HTML
    html = render_report(report_data)

    # Write output
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = BASE_DIR / "outputs"
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = output_dir / f"report_{timestamp}.html"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"\nReport generated: {output_path}")
    logger.info(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"\n✓ Rapor oluşturuldu: {output_path}")


if __name__ == "__main__":
    main()
