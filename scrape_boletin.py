import os
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

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
    Classify the following text as one of these categories:
    - `Relevante`
    - `No relevante`

    Espartina es una empresa que se dedica a la producción de cultívos tradicionales en toda el área agrícola
    de Argentina. El texto a clasificar son resoluciones del boletín oficial de la República Argentina.
    Relevante es toda resolución que establece normas, requisitos, regulaciones o medidas 
    vinculadas a la producción agrícola, su transporte, comercialización o financiamiento. Incluye disposiciones 
    de organismos estatales sobre semillas, agroquímicos, granos, transporte de mercaderías, exportaciones, 
    importaciones, contratos rurales, precios de referencia, impuestos o aspectos ambientales y laborales 
    que puedan impactar directa o indirectamente en la actividad de la empresa.”

    Sólo marca como `Relevante`, las resoluciones que tengan un impacto económico importante y relevante para 
    una empresa que produce principalmente: trigo, soja, maiz, maíz pisingallo, girasol, sorgo, cebada, sesamo, 
    carinata, poroto, garbanzo y arveja. 
    
    Nunca marques como `Relevante` las resoluciones que hablen de Micro, Pequeñas y Medianas Empresas (MiPyMEs) 
    o que no tengan que ver con la producción agrícola, o políticas que puedan impactar en la actividad de la empresa agropecuaria.
    
    Text: {text}
    Only return the category name.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # puedes usar otro modelo según tu plan
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
        model="gpt-4o-mini",  # puedes usar otro modelo según tu plan
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
        model="gpt-4o-mini",  # puedes usar otro modelo según tu plan
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()


# Apply classification
df["Relevancia"] = df["Texto"].apply(classify_text)

relevante_df = df.loc[df["Relevancia"] == "Relevante"]

relevante_df["Resumen"] = relevante_df["Texto"].apply(summarize_text)

relevante_df["Titulo"] = relevante_df["Texto"].apply(create_title)

relevante_df.drop(columns=["Texto", "Relevancia"]).to_excel("~/Downloads/relevante_df.xlsx", index=False)


def generar_html_email_styled(df):
    """
    Genera HTML estilizado para email con las resoluciones del boletín oficial
    """
    hoy = datetime.now().strftime('%d/%m/%Y')
    
    # CSS inline para compatibilidad con clientes de email
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
        <h1 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
            Resoluciones del Boletín Oficial de la última semana
        </h1>
    """
    
    # Loop sobre las filas del DataFrame
    for index, row in df.iterrows():
        fecha = row['Fecha Publicación']
        titulo = row['Titulo']
        resumen = row['Resumen']
        enlace = row['Enlace']
        
        html_content += f"""
        <div style="margin-bottom: 30px; padding: 20px; border: 1px solid #ecf0f1; border-radius: 5px;">
            <h2 style="color: #34495e; margin-top: 0; margin-bottom: 15px; font-size: 18px;">
                {titulo} - {fecha}
            </h2>
            <p style="color: #555; line-height: 1.6; margin-bottom: 15px;">
                {resumen}
            </p>
            <p style="margin-bottom: 0;">
                <a href="{enlace}" style="color: #3498db; text-decoration: none; font-weight: bold;">
                    📋 Ver resolución completa
                </a>
            </p>
        </div>
        """
    
    html_content += "</div>"
    return html_content

# Usar la función con tu DataFrame
html_email_styled = generar_html_email_styled(relevante_df)


import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

# Especificar la ruta exacta del .env
env_path = Path(__file__).parent / '.env'
print(f"Buscando .env en: {env_path}")
print(f"¿Existe el archivo? {env_path.exists()}")

load_dotenv(dotenv_path=env_path, override=True)

email_from = os.getenv('EMAIL_FROM')
print(f"EMAIL_FROM: {email_from}")


test = True


if test:
    email_to = os.getenv('EMAIL_FROM')
else:
    email_to = os.getenv('EMAIL_TO')

print(f"EMAIL_TO: {email_to}")


def enviar_email(mail_to, mail_body):
    msg = EmailMessage()
    msg["Subject"] = f"Principales resoluciones del Boletín Oficial - {hoy}"
    msg["From"] = os.getenv("EMAIL_FROM")
    
    # Handle list of recipients
    if isinstance(mail_to, list):
        msg["To"] = ", ".join(mail_to)
    else:
        msg["To"] = mail_to
    
    # Set plain text fallback and HTML content
    msg.set_content("Este email requiere un cliente que soporte HTML.")
    msg.add_alternative(mail_body, subtype='html')

    # Outlook SMTP con starttls()
    with smtplib.SMTP("smtp-mail.outlook.com", 587) as smtp:
        smtp.starttls()
        smtp.login(os.getenv("EMAIL_FROM"), os.getenv("EMAIL_PASSWORD"))
        smtp.send_message(msg)



try:
    enviar_email(email_to, html_email_styled)
    print(f"✅ Resumen del boletin oficial enviado!")
except Exception as e:
    print(f"Ocurrió un error:\n{e}")