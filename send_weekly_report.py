import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

test = True


# Especificar la ruta exacta del .env
env_path = Path(__file__).parent / '.env'
# print(f"Buscando .env en: {env_path}")
# print(f"¿Existe el archivo? {env_path.exists()}")

load_dotenv(dotenv_path=env_path, override=True)

email_from = os.getenv('EMAIL_FROM')
# print(f"EMAIL_FROM: {email_from}")


if test:
    email_to = os.getenv('EMAIL_FROM')
else:
    email_to = os.getenv('EMAIL_TO')

# print(f"EMAIL_TO: {email_to}")

hoy = datetime.now().strftime('%d/%m/%Y')

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Read the Excel file with relevant resolutions
saved_resolutions = pd.read_excel("resoluciones_relevantes.xlsx", sheet_name="resoluciones_relevantes").copy()


def get_resolutions_last_days(df: pd.DataFrame = saved_resolutions, days: int = 7) -> pd.DataFrame:
    """
    Filters the given DataFrame of relevant resolutions to include only those where 'Fecha Publicación'
    falls within the last `days` days (including today). Also removes from the original file any resolutions
    published before the selected period.

    Args:
        df (pd.DataFrame): DataFrame containing resolutions, must include a 'Fecha Publicación' column in '%d/%m/%Y' format.
        days (int): Number of days to look back from today (default is 7).

    Returns:
        pd.DataFrame: Filtered and sorted DataFrame containing only resolutions published within the specified date range.
    """

    # Convert 'Fecha Publicación' to datetime
    df["Fecha Publicación"] = pd.to_datetime(
        df["Fecha Publicación"], 
        format="%d/%m/%Y", 
        errors="coerce"
    )
    df = df.dropna(subset=["Fecha Publicación"])

    # Calculate the date range
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days-1)

    # Filter rows between start_date and today (inclusive)
    mask = (df["Fecha Publicación"] >= start_date) & (df["Fecha Publicación"] <= end_date)
    filtered_resolutions = df.loc[mask].sort_values(by="Fecha Publicación", ascending=True)

    # Format 'Fecha Publicación' back to string
    filtered_resolutions["Fecha Publicación"] = filtered_resolutions["Fecha Publicación"].dt.strftime("%d/%m/%Y")

    # Remove resolutions older than the selected period from the original file
    # Only do this if the DataFrame is the default (saved_resolutions)
    if df is saved_resolutions:
        # Keep only rows within the period
        updated_df = saved_resolutions.loc[mask].copy()
        # Format 'Fecha Publicación' back to string for saving
        updated_df["Fecha Publicación"] = updated_df["Fecha Publicación"].dt.strftime("%d/%m/%Y")
        # Save back to the Excel file, preserving the same sheet name
        with pd.ExcelWriter("resoluciones_relevantes.xlsx", mode="w", engine="openpyxl") as writer:
            updated_df.to_excel(writer, sheet_name="resoluciones_relevantes", index=False)

    return filtered_resolutions



def build_top_resolutions_payload(df: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
    """
    Prepare the top-N rows to feed the LLM.
    Priority by 'Relevancia' if present; falls back to first rows otherwise.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    work_df = df.copy()
    if "Relevancia" in work_df.columns:
        work_df["Relevancia"] = pd.to_numeric(work_df["Relevancia"], errors="coerce")
        work_df = work_df.sort_values(by="Relevancia", ascending=False, na_position="last")
    return work_df.head(top_n)[["Titulo", "Fecha Publicación", "Resumen", "Enlace", "Relevancia"] if "Relevancia" in work_df.columns else ["Titulo", "Fecha Publicación", "Resumen", "Enlace"]].fillna("")


def generar_resumen_ejecutivo_fallback(df: pd.DataFrame, period_label: str, top_n: int = 3) -> str:
    """
    Simple local fallback if LLM is unavailable. Produces a short paragraph + <ol>.
    """
    if df is None or df.empty:
        return ""

    top = build_top_resolutions_payload(df, top_n=top_n)
    total = len(df)

    # Paragraph
    paragraph = f"""
    <p style="margin:0 0 12px 0; line-height:1.6; color:#34495e;">
        Este informe reúne {total} resoluciones relevantes de {period_label}. A continuación, las {min(top_n, len(top))} de mayor importancia:
    </p>
    """

    # List
    items = []
    for _, row in top.iterrows():
        title = row.get("Titulo", "(Sin título)") or "(Sin título)"
        date_ = row.get("Fecha Publicación", "")
        link = row.get("Enlace", "#") or "#"
        items.append(f'<li style="margin-bottom:6px;"><a href="{link}" style="text-decoration:none; font-weight:600; color:#1b73c4;">{title}</a> — {date_}</li>')

    return f"""
    <div style="background:#f7fbff; border:1px solid #d6e9ff; padding:16px; border-radius:8px; margin:16px 0 24px 0;">
        <h2 style="margin:0 0 8px 0; color:#1f3b57; font-size:18px;">Resumen ejecutivo</h2>
        {paragraph}
        <ol style="margin:0; padding-left:20px;">
            {''.join(items)}
        </ol>
    </div>
    """.strip()


def generar_resumen_ejecutivo_llm(
    df: pd.DataFrame,
    client: OpenAI,
    period_label: str = "la última semana",
    top_n: int = 3,
    model: str = "gpt-4o-mini",
    max_tokens: int = 350,
    temperature: float = 0.2,
) -> str:
    """
    Uses OpenAI to produce an executive summary in Spanish:
    - 1 short paragraph (max ~80-90 words) summarizing the period
    - An <ol> with up to 3 <li> items, each linking to the resolution

    Returns an HTML snippet ready to inject into the email.
    Falls back to a local summary on API/error.
    """
    try:
        if df is None or df.empty:
            return ""

        top = build_top_resolutions_payload(df, top_n=top_n)
        total_count = len(df)

        # Compact payload for the model (truncate long summaries to keep prompt lean)
        records = []
        for _, row in top.iterrows():
            records.append({
                "title": str(row.get("Titulo", ""))[:220],
                "date": str(row.get("Fecha Publicación", ""))[:20],
                "summary": str(row.get("Resumen", ""))[:600],
                "url": str(row.get("Enlace", ""))[:400],
                "relevance": float(row.get("Relevancia", 0)) if "Relevancia" in row else None,
            })

        system_msg = (
            "Eres un asistente editorial que redacta resúmenes ejecutivos breves y claros para emails internos "
            "de una empresa agrícola argentina (Espartina). Debes ser preciso, sin inventar información."
        )

        user_msg = {
            "task": "Escribir un resumen ejecutivo para un email en español.",
            "constraints": {
                "paragraph_word_limit": 90,
                "style": "claro, conciso, orientado a negocio",
                "do_not_invent": True,
            },
            "context": {
                "period_label": period_label,
                "total_relevant_resolutions": total_count,
                "top_items": records,
            },
            "output_spec": {
                "format": "HTML",
                "structure": [
                    "Un párrafo único (<p>) que resuma el período y mencione que se listan las 3 más importantes.",
                    "Una lista ordenada (<ol>) con hasta 3 <li>, cada uno con <a href='URL'>Título</a> — Fecha.",
                ],
                "tone": "profesional",
            },
        }

        # Call the Chat Completions API
        completion = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": f"INSTRUCCIONES:\n{user_msg}"},
            ],
        )

        generated = completion.choices[0].message.content.strip()
        if not generated:
            # Safety fallback if model returns empty content
            return generar_resumen_ejecutivo_fallback(df, period_label=period_label, top_n=top_n)

        # Wrap in our summary card style (in case model returns only inner HTML)
        return f"""
        <div style="background:#f7fbff; border:1px solid #d6e9ff; padding:16px; border-radius:8px; margin:16px 0 24px 0;">
            <h2 style="margin:0 0 8px 0; color:#1f3b57; font-size:18px;">Resumen ejecutivo</h2>
            {generated}
        </div>
        """.strip()

    except Exception as exc:
        # Fallback to deterministic local summary
        return generar_resumen_ejecutivo_fallback(df, period_label=period_label, top_n=top_n)



def generar_html_email_styled(df, period_label: str = "la última semana"):
    """
    Generates styled HTML for an email with Official Bulletin resolutions.
    Includes an executive summary generated by OpenAI.
    """
    hoy = datetime.now().strftime('%d/%m/%Y')

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
        <h1 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
            Resoluciones del Boletín Oficial de la Última Semana
        </h1>
    """

    # >>> NEW: OpenAI-powered executive summary <<<
    html_content += generar_resumen_ejecutivo_llm(
        df=df,
        client=client,
        period_label=period_label,
        top_n=3,
        model="gpt-4o-mini",
        max_tokens=350,
        temperature=0.2,
    )

    # Cards with each resolution
    for _, row in df.iterrows():
        fecha = row.get('Fecha Publicación', '')
        titulo = row.get('Titulo', '(Sin título)') or '(Sin título)'
        resumen = row.get('Resumen', '')
        enlace = row.get('Enlace', '#') or '#'

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


last_resolutions = get_resolutions_last_days()
last_resolutions = last_resolutions.sort_values(by="Relevancia", ascending=False).head(10)

html_email_styled = generar_html_email_styled(last_resolutions, period_label="los últimos 7 días")



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