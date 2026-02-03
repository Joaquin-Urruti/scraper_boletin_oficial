"""Tests for storage module."""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.storage import get_recent_regulations, load_regulations, save_regulations


class TestLoadRegulations:
    """Tests for load_regulations function."""

    def test_load_regulations_empty_file(self, tmp_path: Path) -> None:
        """Test loading from non-existent file returns empty DataFrame."""
        non_existent = tmp_path / "does_not_exist.xlsx"
        result = load_regulations(non_existent)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_load_regulations_with_data(self, test_data_path: Path) -> None:
        """Test loading from existing file returns DataFrame with data."""
        result = load_regulations(test_data_path)

        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "Fecha Publicación" in result.columns

    def test_load_regulations_invalid_file(self, tmp_path: Path) -> None:
        """Test loading invalid file raises exception."""
        invalid_file = tmp_path / "invalid.xlsx"
        invalid_file.write_text("not an excel file")

        with pytest.raises(Exception):
            load_regulations(invalid_file)


class TestSaveRegulations:
    """Tests for save_regulations function."""

    def test_save_regulations_creates_file(
        self, sample_regulations_df: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Test saving creates new Excel file."""
        excel_path = tmp_path / "new_file.xlsx"
        config = MagicMock()
        config.excel_path = excel_path

        save_regulations(sample_regulations_df, config)

        assert excel_path.exists()
        loaded = pd.read_excel(excel_path, sheet_name="resoluciones_relevantes")
        assert len(loaded) == len(sample_regulations_df)

    def test_save_regulations_appends(
        self, sample_regulations_df: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Test saving appends to existing file."""
        excel_path = tmp_path / "existing.xlsx"
        config = MagicMock()
        config.excel_path = excel_path

        # Save initial data
        save_regulations(sample_regulations_df, config)
        initial_count = len(pd.read_excel(excel_path, sheet_name="resoluciones_relevantes"))

        # Append more data
        save_regulations(sample_regulations_df.head(2), config)

        loaded = pd.read_excel(excel_path, sheet_name="resoluciones_relevantes")
        assert len(loaded) == initial_count + 2

    def test_save_regulations_empty_df(self, tmp_path: Path) -> None:
        """Test saving empty DataFrame does nothing."""
        excel_path = tmp_path / "should_not_exist.xlsx"
        config = MagicMock()
        config.excel_path = excel_path

        save_regulations(pd.DataFrame(), config)

        assert not excel_path.exists()

    def test_save_regulations_creates_parent_dirs(
        self, sample_regulations_df: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Test saving creates parent directories if needed."""
        excel_path = tmp_path / "nested" / "dir" / "file.xlsx"
        config = MagicMock()
        config.excel_path = excel_path

        save_regulations(sample_regulations_df, config)

        assert excel_path.exists()


class TestGetRecentRegulations:
    """Tests for get_recent_regulations function."""

    def test_get_recent_regulations_filters_by_date(
        self, sample_regulations_df: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Test filtering regulations by date range."""
        excel_path = tmp_path / "test.xlsx"

        # Save test data
        sample_regulations_df.to_excel(
            excel_path, index=False, sheet_name="resoluciones_relevantes"
        )

        config = MagicMock()
        config.excel_path = excel_path

        result = get_recent_regulations(config, days=3, archive_old=False)

        assert isinstance(result, pd.DataFrame)
        # Should only return regulations from last 3 days
        assert len(result) <= 3

    def test_get_recent_regulations_nonexistent_file(self, tmp_path: Path) -> None:
        """Test returns empty DataFrame when file doesn't exist."""
        config = MagicMock()
        config.excel_path = tmp_path / "nonexistent.xlsx"

        result = get_recent_regulations(config, days=7, archive_old=False)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_get_recent_regulations_empty_file(self, tmp_path: Path) -> None:
        """Test handles empty Excel file."""
        excel_path = tmp_path / "empty.xlsx"

        empty_df = pd.DataFrame(columns=[
            "Fecha Publicación", "Titulo_Generado", "Categoria",
            "Relevancia", "Razonamiento", "Resumen", "Puntos_Clave", "Enlace"
        ])
        empty_df.to_excel(excel_path, index=False, sheet_name="resoluciones_relevantes")

        config = MagicMock()
        config.excel_path = excel_path

        result = get_recent_regulations(config, days=7, archive_old=False)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_get_recent_regulations_archives_old(
        self, sample_regulations_df: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Test archiving removes old regulations from file."""
        excel_path = tmp_path / "test.xlsx"

        # Create data with old dates
        old_dates_df = sample_regulations_df.copy()
        old_dates_df["Fecha Publicación"] = [
            (datetime.now() - timedelta(days=i)).strftime("%d/%m/%Y")
            for i in [0, 1, 10, 15, 20]  # 2 recent, 3 old
        ]
        old_dates_df.to_excel(
            excel_path, index=False, sheet_name="resoluciones_relevantes"
        )

        config = MagicMock()
        config.excel_path = excel_path

        # Get recent with archive=True
        result = get_recent_regulations(config, days=7, archive_old=True)

        # Verify only recent are returned
        assert len(result) == 2

        # Verify file was updated (old entries removed)
        remaining = pd.read_excel(excel_path, sheet_name="resoluciones_relevantes")
        assert len(remaining) == 2

    def test_get_recent_regulations_sorted_by_date(
        self, sample_regulations_df: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Test results are sorted by date ascending."""
        excel_path = tmp_path / "test.xlsx"

        sample_regulations_df.to_excel(
            excel_path, index=False, sheet_name="resoluciones_relevantes"
        )

        config = MagicMock()
        config.excel_path = excel_path

        result = get_recent_regulations(config, days=7, archive_old=False)

        if len(result) > 1:
            dates = pd.to_datetime(result["Fecha Publicación"], format="%d/%m/%Y")
            assert dates.is_monotonic_increasing
