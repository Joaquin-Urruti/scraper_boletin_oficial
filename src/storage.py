"""Excel storage operations for regulations."""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from src.config import Config

logger = logging.getLogger(__name__)

SHEET_NAME = "resoluciones_relevantes"


def load_regulations(excel_path: Path) -> pd.DataFrame:
    """Load regulations from Excel file."""
    if not excel_path.exists():
        logger.info(f"Excel file not found at {excel_path}, returning empty DataFrame")
        return pd.DataFrame()

    try:
        df = pd.read_excel(excel_path, sheet_name=SHEET_NAME)
        logger.info(f"Loaded {len(df)} regulations from {excel_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading Excel file: {e}")
        raise


def save_regulations(df: pd.DataFrame, config: Config) -> None:
    """
    Save regulations to Excel file, appending to existing data.

    Saves columns: Fecha Publicación, Titulo_Generado, Categoria, Relevancia,
    Razonamiento, Resumen, Puntos_Clave, Enlace
    """
    if df.empty:
        logger.info("No regulations to save")
        return

    excel_path = config.excel_path
    excel_path.parent.mkdir(parents=True, exist_ok=True)

    out_df = df[
        [
            "Fecha Publicación",
            "Titulo_Generado",
            "Categoria",
            "Relevancia",
            "Razonamiento",
            "Resumen",
            "Puntos_Clave",
            "Enlace",
        ]
    ].copy()

    if not excel_path.exists():
        out_df.to_excel(excel_path, index=False, sheet_name=SHEET_NAME)
        logger.info(f"Created new file: {excel_path}")
    else:
        with pd.ExcelWriter(
            excel_path, engine="openpyxl", mode="a", if_sheet_exists="overlay"
        ) as writer:
            if SHEET_NAME in writer.book.sheetnames:
                ws = writer.book[SHEET_NAME]
                startrow = ws.max_row
                out_df.to_excel(
                    writer,
                    index=False,
                    sheet_name=SHEET_NAME,
                    startrow=startrow,
                    header=False,
                )
                logger.info(f"Appended {len(out_df)} rows to {excel_path}")
            else:
                out_df.to_excel(writer, index=False, sheet_name=SHEET_NAME)
                logger.info(f"Created new sheet in {excel_path}")


def get_recent_regulations(
    config: Config,
    days: int = 7,
    archive_old: bool = True,
) -> pd.DataFrame:
    """
    Get regulations from the last N days.

    Args:
        config: Application configuration
        days: Number of days to look back
        archive_old: If True, remove older regulations from the file

    Returns:
        DataFrame with recent regulations sorted by date
    """
    excel_path = config.excel_path

    if not excel_path.exists():
        logger.warning(f"Excel file not found: {excel_path}")
        return pd.DataFrame()

    df = pd.read_excel(excel_path, sheet_name=SHEET_NAME).copy()

    if df.empty:
        return df

    # Convert date column
    df["Fecha Publicación"] = pd.to_datetime(
        df["Fecha Publicación"], format="%d/%m/%Y", errors="coerce"
    )
    df = df.dropna(subset=["Fecha Publicación"])

    # Calculate date range
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days - 1)

    # Filter by date
    mask = (df["Fecha Publicación"] >= start_date) & (
        df["Fecha Publicación"] <= end_date
    )
    filtered = df.loc[mask].sort_values(by="Fecha Publicación", ascending=True).copy()

    # Format date back to string
    filtered["Fecha Publicación"] = filtered["Fecha Publicación"].dt.strftime(
        "%d/%m/%Y"
    )

    # Archive old regulations
    if archive_old and mask.sum() < len(df):
        updated_df = df.loc[mask].copy()
        updated_df["Fecha Publicación"] = updated_df["Fecha Publicación"].dt.strftime(
            "%d/%m/%Y"
        )
        with pd.ExcelWriter(excel_path, mode="w", engine="openpyxl") as writer:
            updated_df.to_excel(writer, sheet_name=SHEET_NAME, index=False)
        logger.info(
            f"Archived {len(df) - mask.sum()} old regulations, kept {mask.sum()}"
        )

    logger.info(f"Found {len(filtered)} regulations from the last {days} days")
    return filtered
