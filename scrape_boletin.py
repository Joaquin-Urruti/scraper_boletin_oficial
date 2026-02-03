#!/usr/bin/env python3
"""Daily scraper for Boletín Oficial regulations."""

import sys

from src.classifier import classify_regulations
from src.config import load_config, setup_logging, validate_config
from src.scraper import scrape_regulations
from src.storage import save_regulations


def main() -> int:
    """Main entry point for the scraper."""
    config = load_config()
    logger = setup_logging("scraper", config.log_dir)

    try:
        validate_config(config)
        logger.info("Starting Boletín Oficial scraper")

        # Scrape regulations
        regulations = scrape_regulations()

        if regulations.empty:
            logger.warning("No regulations found")
            return 0

        # Classify and filter relevant regulations
        relevant = classify_regulations(regulations, config)

        if relevant.empty:
            logger.info(
                f"No relevant regulations found (threshold: {config.relevance_threshold})"
            )
            return 0

        # Save to Excel
        save_regulations(relevant, config)
        logger.info(f"Saved {len(relevant)} relevant regulations")

        return 0

    except Exception as e:
        logger.exception(f"Error during scraping: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
