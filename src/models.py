"""Pydantic models for structured OpenAI outputs."""

from pydantic import BaseModel, Field


class RelevanceClassification(BaseModel):
    """Model for text relevance classification."""

    relevance_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Relevance score from 0 to 100 for agricultural production relevance",
    )
    reasoning: str = Field(
        ..., description="Brief explanation of why this score was assigned"
    )


class TextSummary(BaseModel):
    """Model for text summarization."""

    summary: str = Field(..., description="Concise summary of the text in Spanish")
    key_points: list[str] = Field(
        ..., description="List of key points from the text"
    )


class TitleGeneration(BaseModel):
    """Model for title creation."""

    title: str = Field(
        ...,
        max_length=150,
        description="Meaningful title for the text in Spanish",
    )
    category: str = Field(
        ...,
        description="Category or type of regulation (e.g., 'Exportación', 'Semillas', 'Impuestos')",
    )
