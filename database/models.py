from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    id: UUID
    email: str
    display_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Topic(BaseModel):
    id: UUID
    slug: str
    display_name: str

    model_config = ConfigDict(from_attributes=True)


class Problem(BaseModel):
    id: UUID
    title: str
    statement: str
    difficulty: Optional[str] = None
    topic_id: Optional[UUID] = None
    source: Optional[str] = None
    url: Optional[str] = None
    study_priority: Optional[str] = None
    tags: Optional[list[str]] = None
    prerequisites: Optional[list[str]] = None
    interview_relevance: Optional[str] = None
    company_tags: Optional[list[str]] = None
    company_count: Optional[int] = 0
    acceptance_rate: Optional[float] = 0.0
    leetcode_id: Optional[int] = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Mastery(BaseModel):
    user_id: UUID
    topic_id: UUID
    mastery_score: float
    last_practiced_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Attempt(BaseModel):
    id: UUID
    user_id: UUID
    problem_id: UUID
    code_s3_key: Optional[str] = None
    code_blob: Optional[str] = None
    code_language: Optional[str] = "python"
    storage_backend: Optional[str] = "cockroachdb"
    outcome: str
    complexity_achieved: Optional[str] = None
    time_taken_seconds: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
