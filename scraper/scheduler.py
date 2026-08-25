"""Daily scheduling (requirement #1: "scheduled for daily extraction").

Run as a long-lived process: `python -m scraper.scheduler`. Wires an
APScheduler cron job that, once a day at an off-peak hour, sweeps the full
city-pair basket x advance-purchase-window grid for every source, then
re-runs the cleaning pipeline and index construction. Mode ("live" vs
"synthetic") and the schedule time are environment-configurable so the same
code path works for a demo and for a real deployment.

  APIX_SCRAPE_MODE=live|synthetic   (default: synthetic)
  APIX_SCHEDULE_HOUR=0-23           (default: 3)
  APIX_SCHEDULE_MINUTE=0-59         (default: 0)
"""
import argparse
import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from scraper.run import cmd_live, cmd_synthetic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("apix_scraper.scheduler")

MODE = os.environ.get("APIX_SCRAPE_MODE", "synthetic")
SCHEDULE_HOUR = int(os.environ.get("APIX_SCHEDULE_HOUR", "3"))
SCHEDULE_MINUTE = int(os.environ.get("APIX_SCHEDULE_MINUTE", "0"))


def run_daily_job() -> None:
    logger.info("Starting daily APIx acquisition job (mode=%s)", MODE)
    try:
        if MODE == "live":
            cmd_live(argparse.Namespace(sources=None))
        else:
            cmd_synthetic(argparse.Namespace(days=1, end_date=None, seed=42))
    except Exception:
        logger.exception("Daily APIx acquisition job failed")
        raise
    logger.info("Daily APIx acquisition job complete")


def main() -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_daily_job,
        trigger=CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE),
        id="apix_daily_scrape",
        misfire_grace_time=3600,
    )
    logger.info("APIx scheduler started -- daily job at %02d:%02d (mode=%s)", SCHEDULE_HOUR, SCHEDULE_MINUTE, MODE)
    scheduler.start()


if __name__ == "__main__":
    main()
