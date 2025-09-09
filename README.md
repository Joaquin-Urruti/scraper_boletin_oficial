# Boletín Oficial Argentina - Web Scraping & Relevancia Agrícola

## Descripción

Este proyecto realiza web scraping sobre la sección "Primera" del Boletín Oficial de la República Argentina, extrayendo resoluciones y normativas publicadas. Utiliza Python, BeautifulSoup y pandas para recolectar datos como fecha de publicación, título, texto y enlace de cada aviso. Además, emplea la API de OpenAI para:

- Clasificar automáticamente la relevancia de cada resolución para empresas agrícolas argentinas (por ejemplo, Espartina).
- Generar un resumen en español de las resoluciones más relevantes.
- Crear un título significativo para cada resolución relevante.

Las resoluciones clasificadas como más relevantes se almacenan y actualizan en un archivo Excel (`resoluciones_relevantes.xlsx`).

## Instalación

1. Clona este repositorio.
2. Instala las dependencias necesarias:
   ```bash
   pip install -r requirements.txt
   ```
3. Crea un archivo `.env` en la raíz del proyecto con tu clave de OpenAI:
   ```
   OPENAI_API_KEY=tu_clave_de_openai
   ```

## Uso

Ejecuta el script principal para iniciar el scraping, clasificación y generación de resúmenes/títulos: