from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginInput(Contract):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class PasswordInput(Contract):
    current: str = Field(max_length=200)
    new: str = Field(min_length=12, max_length=200)


class ContextBody(Contract):
    profile: str = Field(default="", max_length=12000)
    projects: str = Field(default="", max_length=12000)
    goals: str = Field(default="", max_length=5000)
    audience: str = Field(default="", max_length=5000)
    tone: str = Field(default="", max_length=5000)
    avoid: str = Field(default="", max_length=5000)
    confirmed_facts: str = Field(default="", max_length=10000)
    style_examples: str = Field(default="", max_length=20000)
    references: list[dict] = Field(default_factory=list, max_length=30)


class ContextInput(Contract):
    revision: int
    body: ContextBody


class IdeaProposal(Contract):
    title: str = Field(min_length=3, max_length=300)
    summary: str = Field(min_length=5, max_length=5000)
    angle: str = Field(min_length=3, max_length=5000)
    topic: str = Field(max_length=100)
    content_type: str = Field(max_length=100)
    rationale: str = Field(max_length=5000)
    project_connection: str = Field(default="", max_length=5000)
    current_news: bool = False


class IdeaBatch(Contract):
    ideas: list[IdeaProposal] = Field(max_length=20)
    explanation: str = Field(default="", max_length=4000)


class IdeaGenerate(Contract):
    quantity: int = Field(default=5, ge=1, le=20)
    instructions: str = Field(default="", max_length=5000)
    manual: bool = False
    research: bool = True


class IdeaEdit(IdeaProposal):
    revision: int
    notes: str = Field(default="", max_length=5000)


class IdeaState(Contract):
    status: Literal["pendiente", "seleccionada", "descartada"]
    discard_reason: str = Field(default="", max_length=2000)
    revision: int


class Article(Contract):
    title: str = Field(min_length=3, max_length=300)
    seo_title: str = Field(default="", max_length=300)
    body: str = Field(default="", max_length=150000)
    keyphrase: str = Field(default="", max_length=100)
    slug: str = Field(default="", max_length=200)
    meta_description: str = Field(default="", max_length=500)
    excerpt: str = Field(default="", max_length=3000)
    categories: list[int] = Field(default_factory=list, max_length=30)
    tags: list[int] = Field(default_factory=list, max_length=50)
    image_alt: str = Field(default="", max_length=1000)


class LinkedInText(Contract):
    text: str = Field(max_length=3000)


class ChannelEdit(Contract):
    revision: int
    data: Article | LinkedInText


class Prepare(Contract):
    angle: str = Field(default="", max_length=5000)
    notes: str = Field(default="", max_length=5000)
    keyphrase: str = Field(default="", max_length=100)
    research: bool = True


class Instruction(Contract):
    instructions: str = Field(default="", max_length=5000)


class ConnectionInput(Contract):
    config: dict = Field(default_factory=dict)
    secrets: dict = Field(default_factory=dict)


class ModelOption(Contract):
    id: str = Field(max_length=100)
    provider: Literal["openai", "anthropic"]
    name: str = Field(max_length=200)
    description: str = Field(max_length=1000)
    input: str | None
    output: str | None
    cached: str | None
    cache_write: str | None = None
    search: str | None = "0.01"
    web_search: bool = True
    verified: str
    source: str


class Preferences(Contract):
    app_name: str = Field(default="Germán Content Studio", min_length=1, max_length=100)
    provider: Literal["openai", "anthropic"] = "openai"
    model: str = Field(default="gpt-6.1-sol", max_length=100)
    max_cost: str = "3.00"
    fallback: bool = False
    fallback_provider: Literal["openai", "anthropic"] = "anthropic"
    fallback_model: str = "claude-sonnet-5-5"
    max_ideas: int = Field(default=20, ge=1, le=20)
    max_searches: int = Field(default=3, ge=1, le=5)
    max_output_tokens: int = Field(default=6000, ge=1000, le=12000)
    max_context_chars: int = Field(default=40000, ge=8000, le=80000)


class MetricsInput(Contract):
    start: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    daily: bool = False


class EditorialReview(Contract):
    warnings: list[str] = Field(default_factory=list, max_length=30)
    personal_claims_to_confirm: list[str] = Field(default_factory=list, max_length=30)
    unsupported_claims: list[str] = Field(default_factory=list, max_length=30)
    readability_notes: list[str] = Field(default_factory=list, max_length=30)


class Relation(Contract):
    id: str
    classification: Literal["duplicado", "relacionado", "continuacion", "distinto"]
    reason: str


class Relations(Contract):
    relations: list[Relation] = Field(default_factory=list, max_length=50)
