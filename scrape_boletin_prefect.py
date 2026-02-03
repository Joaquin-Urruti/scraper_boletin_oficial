#!/usr/bin/env python3
"""Daily scraper flow for Boletín Oficial regulations (Prefect-compatible)."""

from __future__ import annotations

import sys

from prefect import flow, get_run_logger, task
from prefect.client.schemas.schedules import CronSchedule

from src.classifier import classify_regulations
from src.config import load_config, setup_logging, validate_config
from src.scraper import scrape_regulations
from src.storage import save_regulations


@task(name="scrape_regulations", retries=2, retry_delay_seconds=60)
def scrape_regulations_task() -> int:
    """Scrape, classify, and persist relevant regulations."""
    config = load_config()
    setup_logging("scraper", config.log_dir)
    logger = get_run_logger()

    try:
        validate_config(config)
        logger.info("Starting Boletín Oficial scraper")

        regulations = scrape_regulations()

        if regulations.empty:
            logger.warning("No regulations found")
            return 0

        relevant = classify_regulations(regulations, config)

        if relevant.empty:
            logger.info(
                "No relevant regulations found (threshold: %s)",
                config.relevance_threshold,
            )
            return 0

        save_regulations(relevant, config)
        logger.info("Saved %s relevant regulations", len(relevant))

        return 0

    except Exception:
        logger.exception("Error during scraping")
        return 1


@flow(name="boletin-oficial-daily-scraper")
def scrape_boletin_flow() -> int:
    """Prefect flow wrapper for the daily Boletín Oficial scraper."""
    return scrape_regulations_task()


def main() -> int:
    """CLI entry point (kept for backwards compatibility)."""
    return scrape_boletin_flow()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        # serve() runs a long-lived process that executes scheduled runs locally
        scrape_boletin_flow.serve(
            name="scrape-boletin-daily",
            schedules=[
                CronSchedule(
                    cron="0 8 * * *", timezone="America/Argentina/Buenos_Aires"
                )
            ],
        )
    else:
        sys.exit(main())
