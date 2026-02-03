"""OpenAI-powered classification and summarization for regulations."""

import logging

import pandas as pd
from openai import OpenAI

from src.config import Config
from src.models import RelevanceClassification, TextSummary, TitleGeneration

logger = logging.getLogger(__name__)


def classify_text(client: OpenAI, text: str, model: str) -> dict:
    """Classify text relevance for agricultural production."""
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
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=RelevanceClassification,
            temperature=0,
        )

        result = response.choices[0].message.parsed
        return {
            "relevance_score": result.relevance_score,
            "reasoning": result.reasoning,
        }
    except Exception as e:
        logger.error(f"Error in classification: {e}")
        return {"relevance_score": 0, "reasoning": "Error in processing"}


def summarize_text(client: OpenAI, text: str, model: str) -> dict:
    """Summarize regulatory text."""
    prompt = f"""
    Summarize the following regulatory text in Spanish, focusing on key aspects relevant to agricultural production.
    Provide a concise summary and identify the main points.

    Text: {text}
    """

    try:
        response = client.beta.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=TextSummary,
            temperature=0,
        )

        result = response.choices[0].message.parsed
        return {"summary": result.summary, "key_points": result.key_points}
    except Exception as e:
        logger.error(f"Error in summarization: {e}")
        return {"summary": "Error en resumen", "key_points": []}


def create_title(client: OpenAI, text: str, model: str) -> dict:
    """Generate a title and category for regulatory text."""
    prompt = f"""
    Create a meaningful title and categorize the following regulatory text in Spanish.
    The title should be descriptive and indicate the main topic of the regulation.

    Text: {text}
    """

    try:
        response = client.beta.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=TitleGeneration,
            temperature=0,
        )

        result = response.choices[0].message.parsed
        return {"title": result.title, "category": result.category}
    except Exception as e:
        logger.error(f"Error in title generation: {e}")
        return {"title": "Título no disponible", "category": "Sin categoría"}


def classify_regulations(df: pd.DataFrame, config: Config) -> pd.DataFrame:
    """
    Classify, filter, and enrich regulations DataFrame.

    Args:
        df: DataFrame with Texto column
        config: Application configuration

    Returns:
        Filtered DataFrame with relevant regulations, enriched with
        Relevancia, Razonamiento, Resumen, Puntos_Clave, Titulo_Generado, Categoria
    """
    if df.empty:
        logger.warning("Empty DataFrame received, nothing to classify")
        return df

    client = OpenAI(api_key=config.openai_api_key)
    model = config.classification_model

    logger.info(f"Classifying {len(df)} regulations...")

    # Apply classification
    classification_results = df["Texto"].apply(
        lambda x: classify_text(client, x, model)
    )
    df["Relevancia"] = classification_results.apply(lambda x: x["relevance_score"])
    df["Razonamiento"] = classification_results.apply(lambda x: x["reasoning"])

    # Filter by relevance threshold
    relevante_df = (
        df[df["Relevancia"].astype(float) > config.relevance_threshold]
        .sort_values(by="Relevancia", ascending=False)
        .head(5)
        .copy()
    )

    if relevante_df.empty:
        logger.info(
            f"No regulations found with relevance > {config.relevance_threshold}"
        )
        return relevante_df

    logger.info(f"Found {len(relevante_df)} relevant regulations, enriching...")

    # Apply summarization
    summary_results = relevante_df["Texto"].apply(
        lambda x: summarize_text(client, x, model)
    )
    relevante_df["Resumen"] = summary_results.apply(lambda x: x["summary"])
    relevante_df["Puntos_Clave"] = summary_results.apply(
        lambda x: "; ".join(x["key_points"])
    )

    # Apply title generation
    title_results = relevante_df["Texto"].apply(
        lambda x: create_title(client, x, model)
    )
    relevante_df["Titulo_Generado"] = title_results.apply(lambda x: x["title"])
    relevante_df["Categoria"] = title_results.apply(lambda x: x["category"])

    logger.info(f"Processed {len(relevante_df)} relevant regulations")

    return relevante_df
