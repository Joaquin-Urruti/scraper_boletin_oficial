#!/usr/bin/env python3
"""Weekly email report flow for Boletín Oficial regulations (Prefect-compatible)."""

from __future__ import annotations

import sys

from prefect import flow, get_run_logger, task
from prefect.client.schemas.schedules import CronSchedule

from src.config import load_config, setup_logging, validate_config
from src.email_service import enviar_email, generar_html_email_styled
from src.storage import get_recent_regulations


@task(name="build_and_send_weekly_report", retries=2, retry_delay_seconds=60)
def send_weekly_report_task(days: int = 7) -> int:
    """Build and send the weekly email report with the top relevant regulations."""
    config = load_config()
    setup_logging("email_report", config.log_dir)
    logger = get_run_logger()

    try:
        validate_config(config, require_email=True)
        logger.info("Starting weekly email report")

        if config.test_mode:
            recipient = config.email_from
            logger.info("TEST MODE: Sending to %s", recipient)
        else:
            recipient = [
                email.strip() for email in config.email_to.split(",") if email.strip()
            ]
            logger.info("Sending to %s recipients", len(recipient))

        regulations = get_recent_regulations(config, days=days, archive_old=True)

        if regulations.empty:
            logger.warning("No regulations found for the past %s days", days)
            return 0

        if "Relevancia" in regulations.columns:
            regulations = regulations.sort_values(
                by="Relevancia", ascending=False
            ).head(10)

        html_body = generar_html_email_styled(
            regulations,
            config,
            period_label=f"los últimos {days} días",
        )

        enviar_email(recipient, html_body, config)
        logger.info("Weekly report sent successfully")

        return 0

    except Exception:
        logger.exception("Error sending weekly report")
        return 1


@flow(name="boletin-oficial-weekly-report")
def send_weekly_report_flow(days: int = 7) -> int:
    """Prefect flow wrapper for the weekly email report."""
    return send_weekly_report_task(days=days)


def main() -> int:
    """CLI entry point (kept for backwards compatibility)."""
    return send_weekly_report_flow()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        # serve() runs a long-lived process that executes scheduled runs locally
        send_weekly_report_flow.serve(
            name="send-weekly-report",
            schedules=[
                CronSchedule(
                    cron="0 9 * * 1", timezone="America/Argentina/Buenos_Aires"
                )
            ],
        )
    else:
        sys.exit(main())
