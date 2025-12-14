import datetime

from pydantic import BaseModel, Field


class AiConfig(BaseModel):
    model: str
    use_google_search: bool

class Error(BaseModel):
    error_type: str
    details: str


class ContentSnippet(BaseModel):
    vehicle_model: str
    category: str
    question: str
    timestamp: datetime.datetime
    response: str
    ai_settings: AiConfig | None = None
    images: list[str] = Field(default_factory=list)
    grounding: str | None = None
    subcategory: str | None = None
    comments: str | None = None
    error: Error | None = None
    embedding: list | None = None


class KnowledgeBase(BaseModel):
    content: list[ContentSnippet] = []
