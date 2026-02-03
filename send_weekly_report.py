#!/usr/bin/env python3
"""Weekly email report sender for Boletín Oficial regulations."""

import sys

from src.config import load_config, setup_logging, validate_config
from src.email_service import enviar_email, generar_html_email_styled
from src.storage import get_recent_regulations


def main() -> int:
    """Main entry point for the weekly report."""
    config = load_config()
    logger = setup_logging("email_report", config.log_dir)

    try:
        validate_config(config, require_email=True)
        logger.info("Starting weekly email report")

        # Determine recipient based on test mode
        if config.test_mode:
            recipient = config.email_from
            logger.info(f"TEST MODE: Sending to {recipient}")
        else:
            # Split email_to by comma if multiple recipients
            recipient = [
                email.strip()
                for email in config.email_to.split(",")
                if email.strip()
            ]
            logger.info(f"Sending to {len(recipient)} recipients")

        # Get recent regulations
        regulations = get_recent_regulations(config, days=7, archive_old=True)

        if regulations.empty:
            logger.warning("No regulations found for the past 7 days")
            return 0

        # Sort by relevance and take top 10
        if "Relevancia" in regulations.columns:
            regulations = regulations.sort_values(
                by="Relevancia", ascending=False
            ).head(10)

        # Generate HTML email
        html_body = generar_html_email_styled(
            regulations, config, period_label="los últimos 7 días"
        )

        # Send email
        enviar_email(recipient, html_body, config)
        logger.info("Weekly report sent successfully")

        return 0

    except Exception as e:
        logger.exception(f"Error sending weekly report: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
