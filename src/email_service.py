"""Email generation and sending service."""

import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage

import pandas as pd
from openai import OpenAI

from src.config import Config

logger = logging.getLogger(__name__)


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

    columns = ["Titulo_Generado", "Fecha Publicación", "Resumen", "Enlace"]
    if "Relevancia" in work_df.columns:
        columns.append("Relevancia")

    available_cols = [c for c in columns if c in work_df.columns]
    return work_df.head(top_n)[available_cols].fillna("")


def generar_resumen_ejecutivo_fallback(
    df: pd.DataFrame, period_label: str, top_n: int = 3
) -> str:
    """Simple local fallback if LLM is unavailable."""
    if df is None or df.empty:
        return ""

    top = build_top_resolutions_payload(df, top_n=top_n)
    total = len(df)

    paragraph = f"""
    <p style="margin:0 0 12px 0; line-height:1.6; color:#34495e;">
        Este informe reúne {total} resoluciones relevantes de {period_label}. A continuación, las {min(top_n, len(top))} de mayor importancia:
    </p>
    """

    items = []
    for _, row in top.iterrows():
        title = row.get("Titulo_Generado", "(Sin título)") or "(Sin título)"
        date_ = row.get("Fecha Publicación", "")
        link = row.get("Enlace", "#") or "#"
        items.append(
            f'<li style="margin-bottom:6px;"><a href="{link}" style="text-decoration:none; font-weight:600; color:#1b73c4;">{title}</a> — {date_}</li>'
        )

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
    Uses OpenAI to produce an executive summary in Spanish.
    Returns an HTML snippet ready to inject into the email.
    Falls back to a local summary on API/error.
    """
    try:
        if df is None or df.empty:
            return ""

        top = build_top_resolutions_payload(df, top_n=top_n)
        total_count = len(df)

        records = []
        for _, row in top.iterrows():
            records.append({
                "title": str(row.get("Titulo_Generado", ""))[:220],
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
            return generar_resumen_ejecutivo_fallback(df, period_label=period_label, top_n=top_n)

        return f"""
        <div style="background:#f7fbff; border:1px solid #d6e9ff; padding:16px; border-radius:8px; margin:16px 0 24px 0;">
            <h2 style="margin:0 0 8px 0; color:#1f3b57; font-size:18px;">Resumen ejecutivo</h2>
            {generated}
        </div>
        """.strip()

    except Exception as exc:
        logger.warning(f"LLM summary failed, using fallback: {exc}")
        return generar_resumen_ejecutivo_fallback(df, period_label=period_label, top_n=top_n)


def generar_html_email_styled(
    df: pd.DataFrame,
    config: Config,
    period_label: str = "la última semana",
) -> str:
    """Generate styled HTML for an email with Official Bulletin resolutions."""
    client = OpenAI(api_key=config.openai_api_key)

    html_content = """
    <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
        <h1 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
            Resoluciones del Boletín Oficial de la Última Semana
        </h1>
    """

    html_content += generar_resumen_ejecutivo_llm(
        df=df,
        client=client,
        period_label=period_label,
        top_n=3,
        model=config.summary_model,
        max_tokens=350,
        temperature=0.2,
    )

    for _, row in df.iterrows():
        fecha = row.get("Fecha Publicación", "")
        titulo = row.get("Titulo_Generado", "(Sin título)") or "(Sin título)"
        resumen = row.get("Resumen", "")
        enlace = row.get("Enlace", "#") or "#"

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
                    Ver resolución completa
                </a>
            </p>
        </div>
        """

    html_content += "</div>"
    return html_content


def enviar_email(recipient: str | list[str], body: str, config: Config) -> None:
    """Send email via SMTP."""
    hoy = datetime.now().strftime("%d/%m/%Y")

    msg = EmailMessage()
    msg["Subject"] = f"Principales resoluciones del Boletín Oficial - {hoy}"
    msg["From"] = config.email_from

    if isinstance(recipient, list):
        msg["To"] = ", ".join(recipient)
    else:
        msg["To"] = recipient

    msg.set_content("Este email requiere un cliente que soporte HTML.")
    msg.add_alternative(body, subtype="html")

    logger.info(f"Sending email to {recipient}")

    try:
        with smtplib.SMTP(config.smtp_server, config.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(config.email_from, config.email_password)
            smtp.send_message(msg)
        logger.info("Email sent successfully")
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        raise
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        raise
