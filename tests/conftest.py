"""Shared fixtures for tests."""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def test_data_path(fixtures_dir: Path) -> Path:
    """Return path to test data Excel file."""
    return fixtures_dir / "test_data.xlsx"


@pytest.fixture
def sample_regulations_df() -> pd.DataFrame:
    """Create a sample DataFrame with regulation data for testing."""
    today = datetime.now()
    dates = [
        (today - timedelta(days=i)).strftime("%d/%m/%Y")
        for i in range(5)
    ]

    return pd.DataFrame({
        "Fecha Publicación": dates,
        "Titulo_Generado": [
            "Regulación sobre exportación de soja",
            "Modificación de aranceles agrícolas",
            "Nueva normativa fitosanitaria",
            "Actualización de precios mínimos",
            "Resolución sobre transporte de granos",
        ],
        "Categoria": ["Exportación", "Aranceles", "Fitosanitaria", "Precios", "Transporte"],
        "Relevancia": [95, 88, 82, 76, 71],
        "Razonamiento": [
            "Afecta directamente la exportación de soja",
            "Impacto en costos de importación",
            "Relevante para certificaciones",
            "Influye en comercialización",
            "Relacionado con logística",
        ],
        "Resumen": [
            "Se establece un nuevo régimen de exportación para soja.",
            "Se modifican los aranceles para productos agrícolas.",
            "Nueva normativa para control fitosanitario.",
            "Actualización de precios mínimos de granos.",
            "Regulación del transporte de granos por carretera.",
        ],
        "Puntos_Clave": [
            "Nuevo régimen; Afecta exportadores",
            "Cambio arancelario; Productos agrícolas",
            "Control fitosanitario; Certificados",
            "Precios mínimos; Mercado interno",
            "Transporte; Normativa vial",
        ],
        "Enlace": [
            "https://boletinoficial.gob.ar/1",
            "https://boletinoficial.gob.ar/2",
            "https://boletinoficial.gob.ar/3",
            "https://boletinoficial.gob.ar/4",
            "https://boletinoficial.gob.ar/5",
        ],
    })


@pytest.fixture
def empty_df() -> pd.DataFrame:
    """Create an empty DataFrame with the expected columns."""
    return pd.DataFrame(columns=[
        "Fecha Publicación",
        "Titulo_Generado",
        "Categoria",
        "Relevancia",
        "Razonamiento",
        "Resumen",
        "Puntos_Clave",
        "Enlace",
    ])


@pytest.fixture
def temp_excel_path(tmp_path: Path) -> Path:
    """Return a temporary path for Excel file operations."""
    return tmp_path / "test_resoluciones.xlsx"
