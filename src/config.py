"""Centralized configuration for the Boletín Oficial scraper."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration."""

    # Paths
    project_dir: Path
    output_dir: Path
    data_dir: Path
    log_dir: Path
    excel_path: Path

    # OpenAI
    openai_api_key: str
    classification_model: str = "gpt-4o-2024-08-06"
    summary_model: str = "gpt-4o-mini"
    relevance_threshold: int = 70

    # Email
    email_from: str = ""
    email_to: str = ""
    email_password: str = ""
    smtp_server: str = "smtp-mail.outlook.com"
    smtp_port: int = 587

    # Mode
    test_mode: bool = False


def load_config() -> Config:
    """Load configuration from environment variables."""
    project_dir = Path(__file__).parent.parent
    env_path = project_dir / ".env"
    load_dotenv(dotenv_path=env_path, override=True)

    output_dir = project_dir / "output"
    data_dir = output_dir / "data"
    log_dir = output_dir / "logs"

    # Ensure directories exist
    data_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    test_mode_env = os.getenv("TEST_MODE", "false").lower()
    test_mode = test_mode_env in ("true", "1", "yes")

    return Config(
        project_dir=project_dir,
        output_dir=output_dir,
        data_dir=data_dir,
        log_dir=log_dir,
        excel_path=data_dir / "resoluciones_relevantes.xlsx",
        openai_api_key=openai_api_key,
        email_from=os.getenv("EMAIL_FROM", ""),
        email_to=os.getenv("EMAIL_TO", ""),
        email_password=os.getenv("EMAIL_PASSWORD", ""),
        test_mode=test_mode,
    )


def setup_logging(name: str, log_dir: Path) -> logging.Logger:
    """Set up logging to both file and console."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Clear existing handlers
    logger.handlers.clear()

    # File handler
    log_file = log_dir / f"{name}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_format)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_format)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def validate_config(config: Config, require_email: bool = False) -> None:
    """Validate that required configuration values are present."""
    if not config.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required")

    if require_email:
        if not config.email_from:
            raise ValueError("EMAIL_FROM is required for sending emails")
        if not config.email_password:
            raise ValueError("EMAIL_PASSWORD is required for sending emails")
        if not config.test_mode and not config.email_to:
            raise ValueError(
                "EMAIL_TO is required when not in test mode"
            )
