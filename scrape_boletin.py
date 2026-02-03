import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Pydantic models for structured outputs
class RelevanceClassification(BaseModel):
    """Model for text relevance classification"""
    relevance_score: int = Field(
        ..., 
        ge=0, 
        le=100,
        description="Relevance score from 0 to 100 for agricultural production relevance"
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of why this score was assigned"
    )

class TextSummary(BaseModel):
    """Model for text summarization"""
    summary: str = Field(
        ...,
        description="Concise summary of the text in Spanish"
    )
    key_points: list[str] = Field(
        ...,
        description="List of key points from the text"
    )

class TitleGeneration(BaseModel):
    """Model for title creation"""
    title: str = Field(
        ...,
        max_length=150,
        description="Meaningful title for the text in Spanish"
    )
    category: str = Field(
        ...,
        description="Category or type of regulation (e.g., 'Exportación', 'Semillas', 'Impuestos')"
    )

# Dictionary to map Spanish months to English
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
    """Function to get publication date"""
    fecha_texto = soup.find('div', class_='margin-bottom-20 fecha-ultima-edicion').find_all('h6')[1].text.strip()
    for mes_es, mes_en in meses.items():
        fecha_texto = fecha_texto.replace(mes_es, mes_en)
    return datetime.strptime(fecha_texto, '%d de %B de %Y').strftime('%d/%m/%Y')

def obtener_detalles_aviso(url_detalle):
    """Function to get notice details"""
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

def classify_text(text: str) -> dict:
    """Use OpenAI structured output to classify the text into categories."""
    prompt = f"""
    Rank the following text from 0 to 100 based on how relevant it is to agricultural production.

    Espartina is a company dedicated to traditional crop production throughout Argentina's agricultural region.
    You will classify texts corresponding to resolutions published in the Official Gazette of the Argentine Republic.

    Consider as "Relevant" (100 points) only those resolutions that establish norms, requirements, regulations 
    or measures that directly and significantly impact agricultural production, transport, commercialization or financing.
    This includes state provisions on seeds, agrochemicals, grains, merchandise transport, exports, imports, 
    rural contracts, reference prices, taxes, or environmental and labor aspects that may directly or indirectly 
    affect agricultural activity.

    Give maximum score (100) only if the resolution has high economic impact and is highly relevant for a company 
    that mainly produces: wheat, soy, corn, popcorn corn, sunflower, sorghum, barley, sesame, carinata, beans, 
    chickpeas and peas.

    Assign 0 points if the resolution deals with Micro, Small and Medium Enterprises (MSMEs), or if it's not 
    related to agricultural production, or if it refers to general policies that don't concretely affect 
    the activity of an agricultural company.

    Be strict: only assign high values to resolutions that can really modify operations, costs, income, 
    regulation or business context of an agricultural company like Espartina.

    Text: {text}
    """
    
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[{"role": "user", "content": prompt}],
            response_format=RelevanceClassification,
            temperature=0
        )
        
        result = response.choices[0].message.parsed
        return {
            "relevance_score": result.relevance_score,
            "reasoning": result.reasoning
        }
    except Exception as e:
        print(f"Error in classification: {e}")
        return {"relevance_score": 0, "reasoning": "Error in processing"}

def summarize_text(text: str) -> dict:
    """Use OpenAI structured output to summarize the text."""
    prompt = f"""
    Summarize the following regulatory text in Spanish, focusing on key aspects relevant to agricultural production.
    Provide a concise summary and identify the main points.

    Text: {text}
    """
    
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[{"role": "user", "content": prompt}],
            response_format=TextSummary,
            temperature=0
        )
        
        result = response.choices[0].message.parsed
        return {
            "summary": result.summary,
            "key_points": result.key_points
        }
    except Exception as e:
        print(f"Error in summarization: {e}")
        return {"summary": "Error en resumen", "key_points": []}

def create_title(text: str) -> dict:
    """Use OpenAI structured output to create a title for the text."""
    prompt = f"""
    Create a meaningful title and categorize the following regulatory text in Spanish.
    The title should be descriptive and indicate the main topic of the regulation.

    Text: {text}
    """
    
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[{"role": "user", "content": prompt}],
            response_format=TitleGeneration,
            temperature=0
        )
        
        result = response.choices[0].message.parsed
        return {
            "title": result.title,
            "category": result.category
        }
    except Exception as e:
        print(f"Error in title generation: {e}")
        return {"title": "Título no disponible", "category": "Sin categoría"}

# Web scraping section
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
        
    except Exception as e:
        print(f"Error al obtener datos de la sección: {e}")

# Apply structured classifications
print("Aplicando clasificaciones con structured outputs...")

# Apply classification and extract structured data
classification_results = df["Texto"].apply(classify_text)
df["Relevancia"] = classification_results.apply(lambda x: x["relevance_score"])
df["Razonamiento"] = classification_results.apply(lambda x: x["reasoning"])

# Filter relevant documents
relevante_df = df[df["Relevancia"].astype(float) > 70].sort_values(by="Relevancia", ascending=False).head(5)

if not relevante_df.empty:
    # Apply summarization
    summary_results = relevante_df["Texto"].apply(summarize_text)
    relevante_df["Resumen"] = summary_results.apply(lambda x: x["summary"])
    relevante_df["Puntos_Clave"] = summary_results.apply(lambda x: "; ".join(x["key_points"]))

    # Apply title generation
    title_results = relevante_df["Texto"].apply(create_title)
    relevante_df["Titulo_Generado"] = title_results.apply(lambda x: x["title"])
    relevante_df["Categoria"] = title_results.apply(lambda x: x["category"])

    # Prepare output dataframe
    out_df = relevante_df[[
        'Fecha Publicación', 'Titulo_Generado', 'Categoria', 'Relevancia', 
        'Razonamiento', 'Resumen', 'Puntos_Clave', 'Enlace'
    ]]

    # Save to Excel
    file_path = "resoluciones_relevantes.xlsx"
    sheet_name = "resoluciones_relevantes"

    if not Path(file_path).exists():
        out_df.to_excel(file_path, index=False, sheet_name=sheet_name)
        print(f"Archivo creado: {file_path}")
    else:
        with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="overlay") as writer:
            if sheet_name in writer.book.sheetnames:
                ws = writer.book[sheet_name]
                startrow = ws.max_row
                out_df.to_excel(
                    writer,
                    index=False,
                    sheet_name=sheet_name,
                    startrow=startrow,
                    header=False,
                )
                print(f"Datos añadidos al archivo existente: {file_path}")
            else:
                out_df.to_excel(writer, index=False, sheet_name=sheet_name)
                print(f"Nueva hoja creada en: {file_path}")

    print(f"Procesadas {len(relevante_df)} resoluciones relevantes")
else:
    print("No se encontraron resoluciones relevantes con puntuación > 70")