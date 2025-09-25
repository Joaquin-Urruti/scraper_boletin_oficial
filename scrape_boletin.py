import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

# Especificar la ruta exacta del .env
env_path = Path(__file__).parent / '.env'
# print(f"Buscando .env en: {env_path}")
# print(f"¿Existe el archivo? {env_path.exists()}")

load_dotenv(dotenv_path=env_path, override=True)


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Diccionario para mapear los meses en español a inglés
meses = {
    'Enero': 'January',
    'Febrero': 'February',
    'Marzo': 'March',
    'Abril': 'April',
    'Mayo': 'May',
    'Junio': 'June',
    'Julio': 'July',
    'Agosto': 'August',
    'Septiembre': 'September',
    'Octubre': 'October',
    'Noviembre': 'November',
    'Diciembre': 'December'
}

hoy = datetime.now().strftime('%d/%m/%Y')

def obtener_fecha_publicacion(soup):
    """Función para obtener la fecha de publicación"""
    fecha_texto = soup.find('div', class_='margin-bottom-20 fecha-ultima-edicion').find_all('h6')[1].text.strip()
    for mes_es, mes_en in meses.items():
        fecha_texto = fecha_texto.replace(mes_es, mes_en)
    return datetime.strptime(fecha_texto, '%d de %B de %Y').strftime('%d/%m/%Y')

def obtener_detalles_aviso(url_detalle):
    """Función para obtener detalles de un aviso"""
    try:
        response_detalle = session.get(url_detalle)
        response_detalle.raise_for_status()
        soup_detalle = BeautifulSoup(response_detalle.text, 'html.parser')
        titulo = soup_detalle.find(id='tituloDetalleAviso').text.strip()
        texto = soup_detalle.find(id='cuerpoDetalleAviso').text.strip()
        return {'Título': titulo, 'Texto': texto, 'Enlace': url_detalle}
    except Exception as e:
        print(f"Error al obtener detalles del aviso: {e}")
        return None

url_base = 'https://www.boletinoficial.gob.ar'
url_seccion = f'{url_base}/seccion/primera'

datos = []

with requests.Session() as session:
    try:
        response = session.get(url_seccion)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        fecha_publicacion = obtener_fecha_publicacion(soup)

        avisos = soup.find_all('div', class_='col-md-12 avisosSeccionDiv')
        for aviso in avisos:
            enlaces = [a['href'] for a in aviso.find_all('a', href=True)]
            for enlace in enlaces:
                url_detalle = f'{url_base}{enlace}'
                detalle_aviso = obtener_detalles_aviso(url_detalle)
                if detalle_aviso:
                    detalle_aviso['Fecha Publicación'] = fecha_publicacion
                    datos.append(detalle_aviso)
        df = pd.DataFrame(datos)
        # df.to_csv(f'~/Library/CloudStorage/GoogleDrive-urrutijoaquin@gmail.com/Mi unidad/boletin_oficial.csv', index=False)
        # df.to_csv(f'./{str(fecha_publicacion).replace("/", "-")}.csv', index=False)
        # df.to_excel(f'./{str(fecha_publicacion).replace("/", "-")}.xlsx', index=False)
    except Exception as e:
        print(f"Error al obtener datos de la sección: {e}")


def classify_text(text):
    """Use OpenAI to classify the text into categories."""
    prompt = f"""
    Rank the following text from 0 to 100 based on how relevant it is to the following topic:
    - `Relevante`: 100
    - `No relevante`: 0

    Espartina es una empresa dedicada a la producción de cultivos tradicionales en toda el región agrícola de Argentina. 
    Vas a clasificar textos que corresponden a resoluciones publicadas en el Boletín Oficial de la República Argentina.

    Considera como "Relevante" (100 puntos) únicamente aquellas resoluciones que establecen normas, requisitos, regulaciones o medidas 
    que impactan directa y significativamente en la producción agrícola, su transporte, comercialización o financiamiento. 
    Esto incluye disposiciones estatales sobre semillas, agroquímicos, granos, transporte de mercaderías, exportaciones, 
    importaciones, contratos rurales, precios de referencia, impuestos, o aspectos ambientales y laborales que puedan afectar 
    la actividad agrícola de manera directa o indirecta.

    Da la máxima puntuación (100) solo si la resolución tiene un impacto económico alto y es muy relevante para una empresa 
    que produce principalmente: trigo, soja, maíz, maíz pisingallo, girasol, sorgo, cebada, sésamo, carinata, poroto, garbanzo y arveja.

    Asigna 0 puntos si la resolución trata sobre Micro, Pequeñas y Medianas Empresas (MiPyMEs), o si no está relacionada 
    con la producción agrícola, o si se refiere a políticas generales que no afectan de manera concreta la actividad de una empresa agropecuaria.

    Sé estricto: solo asigna valores altos a resoluciones que realmente puedan modificar la operatoria, los costos, los ingresos, 
    la regulación o el contexto de negocios de una empresa agrícola como Espartina. Si tienes dudas, asigna un valor bajo.

    Text: {text}
    Only return a number between 0 and 100.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()


def summarize_text(text):
    """Use OpenAI to summarize the text."""
    prompt = f"""
    Summarize the following text: {text} always in spanish.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()


def create_title(text):
    """Use OpenAI to create a title for the text."""
    prompt = f"""
    Create a meaningful title for the following text: {text}, always in spanish.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()


# Apply classification
df["Relevancia"] = df["Texto"].apply(classify_text)

relevante_df = df[df["Relevancia"].astype(float) > 70].sort_values(by="Relevancia", ascending=False).head(5)
relevante_df["Resumen"] = relevante_df["Texto"].apply(summarize_text)
relevante_df["Titulo"] = relevante_df["Texto"].apply(create_title)

# Update the Excel file with the new relevant resolutions
file_path = "resoluciones_relevantes.xlsx"

sheet_name = "resoluciones_relevantes"
out_df = relevante_df.drop(columns=["Texto"])

# Create file if it doesn't exist
if not Path(file_path).exists():
    out_df.to_excel(file_path, index=False, sheet_name=sheet_name)
else:
    # Append to existing sheet (or create it if missing)
    with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="overlay") as writer:
        if sheet_name in writer.book.sheetnames:
            ws = writer.book[sheet_name]
            startrow = ws.max_row  # next empty row (compatible with pandas startrow)
            # Append without header to avoid duplicating column names
            out_df.to_excel(
                writer,
                index=False,
                sheet_name=sheet_name,
                startrow=startrow,
                header=False,
            )
        else:
            # Sheet does not exist yet: write normally with header
            out_df.to_excel(writer, index=False, sheet_name=sheet_name)