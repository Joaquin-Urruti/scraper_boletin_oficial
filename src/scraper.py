"""Web scraping logic for Boletín Oficial."""

import logging
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Spanish to English month mapping for date parsing
MESES = {
    "Enero": "January",
    "Febrero": "February",
    "Marzo": "March",
    "Abril": "April",
    "Mayo": "May",
    "Junio": "June",
    "Julio": "July",
    "Agosto": "August",
    "Septiembre": "September",
    "Octubre": "October",
    "Noviembre": "November",
    "Diciembre": "December",
}

URL_BASE = "https://www.boletinoficial.gob.ar"
URL_SECCION = f"{URL_BASE}/seccion/primera"


def obtener_fecha_publicacion(soup: BeautifulSoup) -> str:
    """Extract publication date from the page."""
    fecha_div = soup.find("div", class_="margin-bottom-20 fecha-ultima-edicion")
    fecha_texto = fecha_div.find_all("h6")[1].text.strip()
    for mes_es, mes_en in MESES.items():
        fecha_texto = fecha_texto.replace(mes_es, mes_en)
    return datetime.strptime(fecha_texto, "%d de %B de %Y").strftime("%d/%m/%Y")


def obtener_detalles_aviso(session: requests.Session, url_detalle: str) -> dict | None:
    """Fetch details for a single notice."""
    try:
        response = session.get(url_detalle)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        titulo = soup.find(id="tituloDetalleAviso").text.strip()
        texto = soup.find(id="cuerpoDetalleAviso").text.strip()
        return {"Título": titulo, "Texto": texto, "Enlace": url_detalle}
    except Exception as e:
        logger.warning(f"Error fetching notice details from {url_detalle}: {e}")
        return None


def scrape_regulations() -> pd.DataFrame:
    """
    Scrape regulations from the Boletín Oficial first section.

    Returns:
        DataFrame with columns: Título, Texto, Enlace, Fecha Publicación
    """
    datos = []

    with requests.Session() as session:
        try:
            logger.info(f"Fetching regulations from {URL_SECCION}")
            response = session.get(URL_SECCION)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            fecha_publicacion = obtener_fecha_publicacion(soup)
            logger.info(f"Publication date: {fecha_publicacion}")

            avisos = soup.find_all("div", class_="col-md-12 avisosSeccionDiv")
            logger.info(f"Found {len(avisos)} notice sections")

            for aviso in avisos:
                enlaces = [a["href"] for a in aviso.find_all("a", href=True)]
                for enlace in enlaces:
                    url_detalle = f"{URL_BASE}{enlace}"
                    detalle = obtener_detalles_aviso(session, url_detalle)
                    if detalle:
                        detalle["Fecha Publicación"] = fecha_publicacion
                        datos.append(detalle)

            logger.info(f"Successfully scraped {len(datos)} regulations")

        except Exception as e:
            logger.error(f"Error scraping section: {e}")
            raise

    return pd.DataFrame(datos)
