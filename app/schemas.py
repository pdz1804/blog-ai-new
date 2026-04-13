from datetime import datetime
from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = Field(default=None)
    abstraction: str = Field(default="")
    tags: list[str] = Field(default_factory=list)
    author_id: str | None = None
    author_name: str | None = Field(default=None)
    source: str | None = Field(default=None)
    url: str | None = Field(default=None)
    citations: list[str] | None = None


class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None)
    abstraction: str | None = Field(default=None)
    tags: list[str] | None = None
    author_id: str | None = None
    author_name: str | None = Field(default=None)
    source: str | None = Field(default=None)
    url: str | None = Field(default=None)
    citations: list[str] | None = None


class ItemOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    abstraction: str
    tags: list[str]
    author_id: str | None = None
    author_name: str | None = None
    source: str | None = None
    url: str | None = None
    citations: list[str] | None = None
    created_date: datetime
    updated_date: datetime


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int


class PagedItems(BaseModel):
    items: list[ItemOut]
    meta: PageMeta


class KeywordSearchResult(BaseModel):
    id: str
    title: str
    snippet: str | None = None
    score: float | None = None
    score_breakdown: dict[str, float] | None = None
    item: ItemOut | None = None
    source: str = "vertex_ai_search"


class FuzzySearchResult(BaseModel):
    item: ItemOut
    score: float
    source: str = "fuzzy"

class TagCount(BaseModel):
    tag: str
    count: int


class PagedItemsByTag(BaseModel):
    tag: str
    items: list[ItemOut]
    meta: PageMeta


class PresignedUrlRequest(BaseModel):
    filename: str = Field(..., min_length=1)
    content_type: str = Field(default="image/jpeg")

class PresignedUrlResponse(BaseModel):
    url: str
    object_name: str
    method: str = "PUT"