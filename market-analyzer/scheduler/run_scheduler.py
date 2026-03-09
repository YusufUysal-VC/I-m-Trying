#!/usr/bin/env python3
"""
run_scheduler.py — APScheduler-based automatic report runner.
Reads schedule from schedule_config.json and runs analyze.py on cron schedule.

Usage:
  python scheduler/run_scheduler.py
  python scheduler/run_scheduler.py --list-schedules
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

logger = logging.getLogger(__name__)


def setup_logging():
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_config() -> dict:
    config_path = Path(__file__).parent / "schedule_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_analysis(job_config: dict) -> None:
    """Run the analysis as a scheduled job."""
    job_name = job_config.get("name", "Unnamed")
    ai_enabled = job_config.get("ai_enabled", False)
    output_dir = job_config.get("output_dir", "./outputs")

    logger.info(f"Starting scheduled job: {job_name}")

    # Import and run main analysis
    try:
        import subprocess
        cmd = [sys.executable, str(PROJECT_ROOT / "analyze.py"), "--output", output_dir]
        if ai_enabled and os.environ.get("ANTHROPIC_API_KEY"):
            cmd.append("--ai")

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Job '{job_name}' completed successfully")
            if result.stdout:
                logger.info(result.stdout[-500:])  # Last 500 chars
        else:
            logger.error(f"Job '{job_name}' failed with code {result.returncode}")
            if result.stderr:
                logger.error(result.stderr[-500:])
    except Exception as e:
        logger.error(f"Job '{job_name}' exception: {e}")


def list_schedules(config: dict) -> None:
    """List upcoming scheduled runs."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        print("APScheduler not installed: pip install apscheduler")
        return

    print(f"\n{'='*60}")
    print("Market Analyzer — Scheduled Jobs")
    print(f"{'='*60}")
    now = datetime.now()

    for job in config.get("jobs", []):
        name = job.get("name", "Unnamed")
        cron_expr = job.get("cron", "")
        description = job.get("description", "")
        ai = "✓ AI" if job.get("ai_enabled") else "✗ No AI"

        # Parse cron to get next run time
        try:
            parts = cron_expr.split()
            if len(parts) >= 5:
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                )
                next_run = trigger.get_next_fire_time(None, now)
                next_str = next_run.strftime("%Y-%m-%d %H:%M") if next_run else "N/A"
            else:
                next_str = "Invalid cron"
        except Exception:
            next_str = "Parse error"

        print(f"\nJob: {name}")
        print(f"  Description: {description}")
        print(f"  Cron:        {cron_expr}")
        print(f"  AI:          {ai}")
        print(f"  Next Run:    {next_str}")

    print(f"\n{'='*60}\n")


def start_scheduler(config: dict) -> None:
    """Start the APScheduler with configured jobs."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler not installed. Run: pip install apscheduler")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone="Europe/Istanbul")

    for job_config in config.get("jobs", []):
        name = job_config.get("name", "job")
        cron_expr = job_config.get("cron", "0 9 * * 1-5")
        parts = cron_expr.split()

        if len(parts) < 5:
            logger.warning(f"Invalid cron expression for job '{name}': {cron_expr}")
            continue

        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            timezone="Europe/Istanbul",
        )

        scheduler.add_job(
            func=run_analysis,
            trigger=trigger,
            args=[job_config],
            id=name,
            name=name,
            replace_existing=True,
        )
        logger.info(f"Scheduled job: {name} — cron: {cron_expr}")

    logger.info("Scheduler started. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Market Analyzer Scheduler")
    parser.add_argument(
        "--list-schedules",
        action="store_true",
        help="List upcoming scheduled runs and exit",
    )
    args = parser.parse_args()

    config = load_config()

    if args.list_schedules:
        list_schedules(config)
    else:
        start_scheduler(config)


if __name__ == "__main__":
    main()
