# Boletín Oficial Argentina - Scraper y Clasificación Agrícola

## Descripción

Sistema automatizado para monitorear regulaciones agrícolas del Boletín Oficial de la República Argentina. El proyecto:

1. **Scraping diario**: Extrae resoluciones de la sección "Primera" del Boletín Oficial
2. **Clasificación con IA**: Usa OpenAI para evaluar relevancia para empresas agrícolas (0-100)
3. **Resumen automático**: Genera resúmenes y títulos descriptivos en español
4. **Reporte semanal**: Envía emails con las resoluciones más relevantes

**Público objetivo**: Espartina, productora de cultivos tradicionales (trigo, soja, maíz, girasol, sorgo, cebada, sésamo, porotos, garbanzos, arvejas) en Argentina.

## Estructura del Proyecto

```
scraper_boletin_oficial/
├── src/                      # Módulos principales
│   ├── config.py             # Configuración centralizada
│   ├── models.py             # Modelos Pydantic para OpenAI
│   ├── scraper.py            # Lógica de web scraping
│   ├── classifier.py         # Clasificación con OpenAI
│   ├── email_service.py      # Generación y envío de emails
│   └── storage.py            # Persistencia en Excel
├── tests/                    # Suite de tests
│   ├── conftest.py           # Fixtures compartidos
│   ├── test_config.py        # Tests de configuración
│   ├── test_email_service.py # Tests de email
│   ├── test_storage.py       # Tests de persistencia
│   └── fixtures/             # Datos de prueba
├── output/                   # Archivos generados
│   ├── data/                 # Excel con resoluciones
│   └── logs/                 # Logs de ejecución
├── scrape_boletin.py         # CLI: scraper diario
├── send_weekly_report.py     # CLI: reporte semanal
├── pyproject.toml            # Dependencias (uv)
├── .env                      # Variables de entorno
└── .env.example              # Template de configuración
```

## Instalación

### Requisitos
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (gestor de paquetes)

### Pasos

1. Clona el repositorio:
   ```bash
   git clone <repo-url>
   cd scraper_boletin_oficial
   ```

2. Instala dependencias:
   ```bash
   uv sync
   ```

3. Configura las variables de entorno:
   ```bash
   cp .env.example .env
   # Edita .env con tus credenciales
   ```

## Configuración

Crea un archivo `.env` con las siguientes variables:

```env
# OpenAI (requerido)
OPENAI_API_KEY=sk-tu-clave-aqui

# Email (requerido para reportes)
EMAIL_FROM=tu-email@outlook.com
EMAIL_PASSWORD=tu-app-password
EMAIL_TO=destinatario1@example.com, destinatario2@example.com

# Modo de prueba (opcional, default: false)
# true = emails solo al remitente, false = emails a destinatarios reales
TEST_MODE=false
```

## Uso

### Scraper Diario

Ejecuta el scraper para obtener y clasificar las resoluciones del día:

```bash
uv run python scrape_boletin.py
```

Este comando:
- Scrapea la sección "Primera" del Boletín Oficial
- Clasifica cada resolución (relevancia 0-100)
- Filtra las que superan el umbral (>70 puntos)
- Genera resúmenes y títulos para las relevantes
- Guarda en `output/data/resoluciones_relevantes.xlsx`

### Reporte Semanal

Envía un email con las resoluciones de los últimos 7 días:

```bash
uv run python send_weekly_report.py
```

Para probar sin enviar a los destinatarios reales:

```bash
TEST_MODE=true uv run python send_weekly_report.py
```

### Logs

Los logs se guardan en `output/logs/`:
- `scraper.log` - Logs del scraper diario
- `email_report.log` - Logs del reporte semanal

## Tests

Instala las dependencias de desarrollo:

```bash
uv sync --all-extras
```

Ejecuta los tests:

```bash
uv run pytest tests/ -v
```

La suite incluye 40 tests cubriendo:
- `test_config.py` - Carga de configuración, variables de entorno, logging
- `test_storage.py` - Lectura/escritura de Excel, filtrado por fecha
- `test_email_service.py` - Generación de HTML, resúmenes, payloads

## Automatización

### Cron (Linux/Mac)

```bash
# Scraper diario a las 8:00 AM
0 8 * * * cd /ruta/al/proyecto && uv run python scrape_boletin.py

# Reporte semanal los lunes a las 9:00 AM
0 9 * * 1 cd /ruta/al/proyecto && uv run python send_weekly_report.py
```

### Task Scheduler (Windows)

Crea tareas programadas para ejecutar los scripts con `uv run python`.

## Tecnologías

- **BeautifulSoup4**: Web scraping
- **OpenAI API**: Clasificación y resúmenes (gpt-4o-2024-08-06, gpt-4o-mini)
- **Pandas + OpenPyXL**: Manejo de datos y Excel
- **Pydantic**: Structured outputs de OpenAI
- **python-dotenv**: Variables de entorno
- **pytest**: Testing (dev dependency)

## Umbrales y Configuración

| Parámetro | Valor | Ubicación |
|-----------|-------|-----------|
| Umbral de relevancia | 70 | `src/config.py` |
| Modelo clasificación | gpt-4o-2024-08-06 | `src/config.py` |
| Modelo resumen email | gpt-4o-mini | `src/config.py` |
| Top resoluciones guardadas | 5 | `src/classifier.py` |
| Top resoluciones en email | 10 | `send_weekly_report.py` |
