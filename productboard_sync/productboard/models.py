from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator


class OwnerRef(BaseModel):
    id: Optional[str] = None
    email: Optional[str] = None


class TagRef(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None


class StatusRef(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None


class Timeframe(BaseModel):
    startDate: Optional[str] = None
    endDate: Optional[str] = None


class EntityFields(BaseModel):
    model_config = {"extra": "allow"}

    name: Optional[str] = None
    owner: Optional[OwnerRef] = None
    tags: Optional[list[TagRef]] = Field(default_factory=list)
    status: Optional[StatusRef] = None
    timeframe: Optional[Timeframe] = None
    archived: Optional[bool] = None


class RelationshipTarget(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None


class Relationship(BaseModel):
    type: Optional[str] = None
    target: Optional[RelationshipTarget] = None


class Links(BaseModel):
    self_: Optional[str] = Field(None, alias="self")
    html: Optional[str] = None


class Entity(BaseModel):
    id: str
    type: str
    fields: EntityFields = Field(default_factory=EntityFields)
    relationships: Optional[list[Relationship]] = None
    links: Optional[Links] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

    @field_validator("relationships", mode="before")
    @classmethod
    def unwrap_relationships(cls, v):
        if isinstance(v, dict):
            return v.get("data")
        return v


class NoteContentMessage(BaseModel):
    externalId: Optional[str] = None
    content: Optional[str] = None
    authorName: Optional[str] = None
    authorType: Optional[str] = None
    timestamp: Optional[str] = None


class NoteFields(BaseModel):
    name: Optional[str] = None
    content: Optional[Union[str, list[NoteContentMessage]]] = None
    tags: Optional[list[TagRef]] = Field(default_factory=list)
    owner: Optional[OwnerRef] = None
    creator: Optional[OwnerRef] = None
    processed: Optional[bool] = None
    archived: Optional[bool] = None


class Note(BaseModel):
    id: str
    type: str
    fields: NoteFields = Field(default_factory=NoteFields)
    relationships: Optional[list[Relationship]] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

    @field_validator("relationships", mode="before")
    @classmethod
    def unwrap_relationships(cls, v):
        if isinstance(v, dict):
            return v.get("data")
        return v


class MemberFields(BaseModel):
    model_config = {"extra": "ignore"}

    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    disabled: Optional[bool] = None


class Member(BaseModel):
    id: str
    type: str = "member"
    fields: MemberFields = Field(default_factory=MemberFields)
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class TeamFields(BaseModel):
    model_config = {"extra": "ignore"}

    name: Optional[str] = None
    handle: Optional[str] = None
    description: Optional[str] = None


class Team(BaseModel):
    id: str
    type: str = "team"
    fields: TeamFields = Field(default_factory=TeamFields)
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class EntityFieldConfig(BaseModel):
    model_config = {"extra": "ignore"}

    id: str
    name: Optional[str] = None


class EntityConfiguration(BaseModel):
    type: Optional[str] = None
    fields: list[EntityFieldConfig] = Field(default_factory=list)

    @field_validator("fields", mode="before")
    @classmethod
    def normalize_fields(cls, v):
        if isinstance(v, dict):
            return list(v.values())
        return v


class PaginatedLinks(BaseModel):
    next: Optional[str] = None


class PaginatedResponse(BaseModel):
    data: list[Any] = Field(default_factory=list)
    links: Optional[PaginatedLinks] = None
