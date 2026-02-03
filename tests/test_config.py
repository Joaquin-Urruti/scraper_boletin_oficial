"""Tests for config module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import Config, load_config, setup_logging, validate_config


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_missing_api_key(self, tmp_path: Path) -> None:
        """Test raises error when OPENAI_API_KEY is missing."""
        env_vars = {
            "OPENAI_API_KEY": "",
            "EMAIL_FROM": "test@example.com",
            "EMAIL_TO": "recipient@example.com",
            "EMAIL_PASSWORD": "password",
            "TEST_MODE": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("src.config.load_dotenv"):
                with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                    load_config()

    def test_load_config_creates_directories(self, tmp_path: Path) -> None:
        """Test creates output directories on load."""
        env_vars = {
            "OPENAI_API_KEY": "sk-test-key",
            "EMAIL_FROM": "test@example.com",
            "EMAIL_TO": "recipient@example.com",
            "EMAIL_PASSWORD": "password",
            "TEST_MODE": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("src.config.load_dotenv"):
                config = load_config()

                # Directories should exist after load
                assert config.data_dir.exists()
                assert config.log_dir.exists()

    def test_test_mode_from_env_true(self) -> None:
        """Test TEST_MODE=true is read correctly."""
        env_vars = {
            "OPENAI_API_KEY": "sk-test-key",
            "TEST_MODE": "true",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("src.config.load_dotenv"):
                config = load_config()
                assert config.test_mode is True

    def test_test_mode_from_env_false(self) -> None:
        """Test TEST_MODE=false is read correctly."""
        env_vars = {
            "OPENAI_API_KEY": "sk-test-key",
            "TEST_MODE": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("src.config.load_dotenv"):
                config = load_config()
                assert config.test_mode is False

    def test_test_mode_from_env_1(self) -> None:
        """Test TEST_MODE=1 is read as True."""
        env_vars = {
            "OPENAI_API_KEY": "sk-test-key",
            "TEST_MODE": "1",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("src.config.load_dotenv"):
                config = load_config()
                assert config.test_mode is True

    def test_test_mode_default_is_false(self) -> None:
        """Test TEST_MODE defaults to False when not set."""
        env_vars = {
            "OPENAI_API_KEY": "sk-test-key",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("src.config.load_dotenv"):
                # Remove TEST_MODE if it exists
                os.environ.pop("TEST_MODE", None)
                config = load_config()
                assert config.test_mode is False


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_validate_config_missing_api_key(self) -> None:
        """Test raises error when API key is empty."""
        config = Config(
            project_dir=Path("/tmp"),
            output_dir=Path("/tmp/output"),
            data_dir=Path("/tmp/output/data"),
            log_dir=Path("/tmp/output/logs"),
            excel_path=Path("/tmp/output/data/test.xlsx"),
            openai_api_key="",
        )

        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            validate_config(config)

    def test_validate_config_email_required_missing_from(self) -> None:
        """Test raises error when email_from is missing in email mode."""
        config = Config(
            project_dir=Path("/tmp"),
            output_dir=Path("/tmp/output"),
            data_dir=Path("/tmp/output/data"),
            log_dir=Path("/tmp/output/logs"),
            excel_path=Path("/tmp/output/data/test.xlsx"),
            openai_api_key="sk-test",
            email_from="",
            email_password="password",
        )

        with pytest.raises(ValueError, match="EMAIL_FROM"):
            validate_config(config, require_email=True)

    def test_validate_config_email_required_missing_password(self) -> None:
        """Test raises error when email_password is missing in email mode."""
        config = Config(
            project_dir=Path("/tmp"),
            output_dir=Path("/tmp/output"),
            data_dir=Path("/tmp/output/data"),
            log_dir=Path("/tmp/output/logs"),
            excel_path=Path("/tmp/output/data/test.xlsx"),
            openai_api_key="sk-test",
            email_from="test@example.com",
            email_password="",
        )

        with pytest.raises(ValueError, match="EMAIL_PASSWORD"):
            validate_config(config, require_email=True)

    def test_validate_config_email_required_missing_to_not_test_mode(self) -> None:
        """Test raises error when email_to missing and not in test mode."""
        config = Config(
            project_dir=Path("/tmp"),
            output_dir=Path("/tmp/output"),
            data_dir=Path("/tmp/output/data"),
            log_dir=Path("/tmp/output/logs"),
            excel_path=Path("/tmp/output/data/test.xlsx"),
            openai_api_key="sk-test",
            email_from="test@example.com",
            email_password="password",
            email_to="",
            test_mode=False,
        )

        with pytest.raises(ValueError, match="EMAIL_TO"):
            validate_config(config, require_email=True)

    def test_validate_config_email_test_mode_allows_empty_to(self) -> None:
        """Test email_to can be empty in test mode."""
        config = Config(
            project_dir=Path("/tmp"),
            output_dir=Path("/tmp/output"),
            data_dir=Path("/tmp/output/data"),
            log_dir=Path("/tmp/output/logs"),
            excel_path=Path("/tmp/output/data/test.xlsx"),
            openai_api_key="sk-test",
            email_from="test@example.com",
            email_password="password",
            email_to="",
            test_mode=True,
        )

        # Should not raise
        validate_config(config, require_email=True)


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_creates_logger(self, tmp_path: Path) -> None:
        """Test creates a logger with the given name."""
        logger = setup_logging("test_logger", tmp_path)

        assert logger.name == "test_logger"
        assert len(logger.handlers) == 2  # File + console

    def test_setup_logging_creates_log_file(self, tmp_path: Path) -> None:
        """Test creates log file in specified directory."""
        logger = setup_logging("test_app", tmp_path)

        log_file = tmp_path / "test_app.log"
        assert log_file.exists()

    def test_setup_logging_writes_to_file(self, tmp_path: Path) -> None:
        """Test log messages are written to file."""
        logger = setup_logging("test_writer", tmp_path)
        logger.info("Test message")

        # Force flush
        for handler in logger.handlers:
            handler.flush()

        log_file = tmp_path / "test_writer.log"
        content = log_file.read_text()
        assert "Test message" in content
