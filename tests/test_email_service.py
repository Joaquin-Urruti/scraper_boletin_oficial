"""Tests for email_service module."""

import pandas as pd
import pytest

from src.email_service import (
    build_top_resolutions_payload,
    generar_html_email_styled,
    generar_resumen_ejecutivo_fallback,
)


class TestBuildTopResolutionsPayload:
    """Tests for build_top_resolutions_payload function."""

    def test_build_top_resolutions_payload_empty(self) -> None:
        """Test with empty DataFrame returns empty DataFrame."""
        result = build_top_resolutions_payload(pd.DataFrame())

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_build_top_resolutions_payload_none(self) -> None:
        """Test with None returns empty DataFrame."""
        result = build_top_resolutions_payload(None)

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_build_top_resolutions_payload_selects_top_n(
        self, sample_regulations_df: pd.DataFrame
    ) -> None:
        """Test selects top N by relevance."""
        result = build_top_resolutions_payload(sample_regulations_df, top_n=3)

        assert len(result) == 3
        # Should be sorted by relevance descending
        assert result.iloc[0]["Relevancia"] >= result.iloc[1]["Relevancia"]
        assert result.iloc[1]["Relevancia"] >= result.iloc[2]["Relevancia"]

    def test_build_top_resolutions_payload_fewer_than_n(
        self, sample_regulations_df: pd.DataFrame
    ) -> None:
        """Test handles fewer rows than requested."""
        small_df = sample_regulations_df.head(2)
        result = build_top_resolutions_payload(small_df, top_n=5)

        assert len(result) == 2

    def test_build_top_resolutions_payload_includes_required_columns(
        self, sample_regulations_df: pd.DataFrame
    ) -> None:
        """Test result includes required columns."""
        result = build_top_resolutions_payload(sample_regulations_df, top_n=3)

        expected_cols = ["Titulo_Generado", "Fecha Publicación", "Resumen", "Enlace"]
        for col in expected_cols:
            assert col in result.columns

    def test_build_top_resolutions_payload_without_relevancia(self) -> None:
        """Test handles DataFrame without Relevancia column."""
        df = pd.DataFrame({
            "Titulo_Generado": ["Title 1", "Title 2"],
            "Fecha Publicación": ["01/01/2024", "02/01/2024"],
            "Resumen": ["Summary 1", "Summary 2"],
            "Enlace": ["http://link1", "http://link2"],
        })

        result = build_top_resolutions_payload(df, top_n=2)

        assert len(result) == 2
        assert "Relevancia" not in result.columns


class TestGenerarResumenEjecutivoFallback:
    """Tests for generar_resumen_ejecutivo_fallback function."""

    def test_fallback_empty_df(self) -> None:
        """Test with empty DataFrame returns empty string."""
        result = generar_resumen_ejecutivo_fallback(pd.DataFrame(), "la última semana")

        assert result == ""

    def test_fallback_none_df(self) -> None:
        """Test with None returns empty string."""
        result = generar_resumen_ejecutivo_fallback(None, "la última semana")

        assert result == ""

    def test_fallback_generates_html(
        self, sample_regulations_df: pd.DataFrame
    ) -> None:
        """Test generates valid HTML structure."""
        result = generar_resumen_ejecutivo_fallback(
            sample_regulations_df, "la última semana", top_n=3
        )

        assert isinstance(result, str)
        assert len(result) > 0
        assert "<div" in result
        assert "Resumen ejecutivo" in result
        assert "<ol" in result
        assert "<li" in result

    def test_fallback_includes_regulation_count(
        self, sample_regulations_df: pd.DataFrame
    ) -> None:
        """Test includes total regulation count in text."""
        result = generar_resumen_ejecutivo_fallback(
            sample_regulations_df, "la última semana"
        )

        assert str(len(sample_regulations_df)) in result

    def test_fallback_includes_links(
        self, sample_regulations_df: pd.DataFrame
    ) -> None:
        """Test includes links to regulations."""
        result = generar_resumen_ejecutivo_fallback(
            sample_regulations_df, "la última semana", top_n=3
        )

        assert "href=" in result
        assert "boletinoficial.gob.ar" in result


class TestGenerarHtmlEmailStyled:
    """Tests for generar_html_email_styled function - basic structure only."""

    def test_styled_html_not_empty_with_empty_df(self) -> None:
        """Test generates basic structure even with empty DataFrame."""
        # Note: This test doesn't call the actual function to avoid API calls
        # Instead, we test the fallback behavior of related functions
        from unittest.mock import MagicMock, patch

        empty_df = pd.DataFrame()
        config = MagicMock()
        config.openai_api_key = "test-key"
        config.summary_model = "gpt-4o-mini"

        # Mock OpenAI to avoid actual API calls
        with patch("src.email_service.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = "<p>Test summary</p>"
            mock_client.chat.completions.create.return_value = mock_completion

            result = generar_html_email_styled(empty_df, config)

            assert isinstance(result, str)
            assert "<div" in result
            assert "Boletín Oficial" in result

    def test_styled_html_structure_with_data(
        self, sample_regulations_df: pd.DataFrame
    ) -> None:
        """Test generates proper HTML structure with data."""
        from unittest.mock import MagicMock, patch

        config = MagicMock()
        config.openai_api_key = "test-key"
        config.summary_model = "gpt-4o-mini"

        with patch("src.email_service.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = "<p>Test summary</p>"
            mock_client.chat.completions.create.return_value = mock_completion

            result = generar_html_email_styled(sample_regulations_df, config)

            assert isinstance(result, str)
            # Check main structure
            assert "<h1" in result
            assert "Boletín Oficial" in result
            # Check regulations are included
            assert "Ver resolución completa" in result

    def test_styled_html_uses_fallback_on_error(
        self, sample_regulations_df: pd.DataFrame
    ) -> None:
        """Test falls back to local summary on API error."""
        from unittest.mock import MagicMock, patch

        config = MagicMock()
        config.openai_api_key = "test-key"
        config.summary_model = "gpt-4o-mini"

        with patch("src.email_service.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Simulate API error
            mock_client.chat.completions.create.side_effect = Exception("API Error")

            result = generar_html_email_styled(sample_regulations_df, config)

            # Should still generate HTML using fallback
            assert isinstance(result, str)
            assert "<div" in result
            assert "Resumen ejecutivo" in result
