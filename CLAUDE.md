# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A web scraper and AI-powered classification system for monitoring Argentine agricultural regulations from the Boletín Oficial (Official Gazette). The system scrapes regulations daily, classifies their relevance to agricultural companies using OpenAI, and sends weekly email summaries.

**Target audience**: Espartina, a traditional crop producer (wheat, soy, corn, sunflower, sorghum, barley, sesame, beans, chickpeas, peas) throughout Argentina.

## Commands

```bash
# Install dependencies
uv sync

# Install dev dependencies (includes pytest)
uv sync --all-extras

# Run daily scraper (fetches, classifies, stores relevant regulations)
uv run python scrape_boletin.py

# Send weekly email report
uv run python send_weekly_report.py

# Run tests
uv run pytest tests/ -v
```

## Architecture

### Module Structure

```
src/
├── config.py        # Centralized configuration, logging, env vars
├── models.py        # Pydantic models for OpenAI structured outputs
├── scraper.py       # Web scraping logic (BeautifulSoup)
├── classifier.py    # OpenAI classification and summarization
├── email_service.py # HTML generation and SMTP sending
└── storage.py       # Excel persistence (read/write/filter)
```

### Data Pipeline

1. **scrape_boletin.py** - Daily scraping and AI classification
   - Scrapes `https://www.boletinoficial.gob.ar/seccion/primera`
   - Extracts: date, title, body text, link
   - Three OpenAI calls per regulation using structured outputs:
     - `classify_text()` → relevance score (0-100) + reasoning
     - `summarize_text()` → Spanish summary + key points
     - `create_title()` → generated title + category
   - Filters regulations with score > 70
   - Appends to `output/data/resoluciones_relevantes.xlsx`

2. **send_weekly_report.py** - Weekly email distribution
   - Loads last 7 days of regulations from Excel
   - Archives older entries (removes from file)
   - Generates AI executive summary via `gpt-4o-mini`
   - Sends styled HTML email via Outlook SMTP

### Pydantic Models (src/models.py)

```python
RelevanceClassification  # relevance_score: int, reasoning: str
TextSummary              # summary: str, key_points: list[str]
TitleGeneration          # title: str, category: str
```

### Key Paths

- `output/data/resoluciones_relevantes.xlsx` - Persistent storage
- `output/logs/scraper.log` - Scraper execution logs
- `output/logs/email_report.log` - Email report logs
- `.env` - Environment variables (not committed)

### Excel Columns

```
Fecha Publicación, Titulo_Generado, Categoria, Relevancia,
Razonamiento, Resumen, Puntos_Clave, Enlace
```

## Environment Variables

```
OPENAI_API_KEY=sk-...
EMAIL_FROM=sender@outlook.com
EMAIL_TO=recipient@example.com
EMAIL_PASSWORD=outlook-app-password
TEST_MODE=false  # true = emails only to sender
```

## Configuration (src/config.py)

| Setting | Default | Description |
|---------|---------|-------------|
| `relevance_threshold` | 70 | Minimum score to save regulation |
| `classification_model` | gpt-4o-2024-08-06 | Model for classification |
| `summary_model` | gpt-4o-mini | Model for email summaries |
| `smtp_server` | smtp-mail.outlook.com | SMTP server |
| `smtp_port` | 587 | SMTP port |

## Tests

```bash
uv run pytest tests/ -v
```

Test coverage:
- `test_config.py` - Config loading, env vars, logging setup
- `test_storage.py` - Excel read/write, date filtering, archiving
- `test_email_service.py` - HTML generation, payloads, fallbacks

## Dependencies

Managed with `uv`. Key packages: `beautifulsoup4`, `requests`, `pandas`, `openai`, `openpyxl`, `python-dotenv`

Dev: `pytest`

Requires Python 3.12+
