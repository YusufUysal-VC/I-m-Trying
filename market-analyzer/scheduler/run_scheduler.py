#!/usr/bin/env python3
"""
APScheduler-based automatic runner for Market Analyzer.
Reads schedule_config.json and runs analyses at configured times.
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEDULER_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCHEDULER_DIR / "schedule_config.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load scheduler configuration."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_analysis(job_name: str, ai_enabled: bool, output_dir: str):
    """Execute the analyzer as a subprocess."""
    logger.info(f"Running scheduled job: {job_name}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_file = output_path / f"report_{timestamp}.html"

    cmd = [sys.executable, str(BASE_DIR / "analyze.py"), "--output", str(output_file)]
    if ai_enabled:
        cmd.append("--ai")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            logger.info(f"Job '{job_name}' completed successfully: {output_file}")
        else:
            logger.error(f"Job '{job_name}' failed:\n{result.stderr}")
    except subprocess.TimeoutExpired:
        logger.error(f"Job '{job_name}' timed out after 10 minutes")
    except Exception as e:
        logger.error(f"Job '{job_name}' error: {e}")


def list_schedules(config: dict):
    """Display configured schedules."""
    print("\n📅 Yapılandırılmış Zamanlamalar:")
    print("-" * 60)
    for job in config.get("jobs", []):
        ai_label = "✓" if job.get("ai_enabled") else "✗"
        print(f"  {job['name']}")
        print(f"    Cron: {job['cron']}")
        print(f"    Açıklama: {job.get('description', '—')}")
        print(f"    AI: {ai_label}")
        print(f"    Çıktı: {job.get('output_dir', './outputs')}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Market Analyzer Scheduler")
    parser.add_argument("--list-schedules", action="store_true", help="Show configured schedules")
    parser.add_argument("--config", type=str, help="Path to schedule config JSON")
    args = parser.parse_args()

    global CONFIG_PATH
    if args.config:
        CONFIG_PATH = Path(args.config)

    config = load_config()

    if args.list_schedules:
        list_schedules(config)
        return

    scheduler = BlockingScheduler()

    for job in config.get("jobs", []):
        cron_parts = job["cron"].split()
        if len(cron_parts) != 5:
            logger.warning(f"Invalid cron expression for '{job['name']}': {job['cron']}")
            continue

        trigger = CronTrigger(
            minute=cron_parts[0],
            hour=cron_parts[1],
            day=cron_parts[2],
            month=cron_parts[3],
            day_of_week=cron_parts[4],
        )

        scheduler.add_job(
            run_analysis,
            trigger=trigger,
            args=[job["name"], job.get("ai_enabled", False), job.get("output_dir", "./outputs")],
            id=job["name"],
            name=job["name"],
        )
        logger.info(f"Scheduled: {job['name']} ({job['cron']})")

    logger.info("Scheduler started. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
