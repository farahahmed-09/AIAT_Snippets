from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ProjectRole = Literal["manager", "editor", "viewer"]


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None


class Project(ProjectBase):
    id: int
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class Membership(BaseModel):
    """A single (project, user, role) row."""

    project_id: int
    user_id: str
    role: ProjectRole
    joined_at: datetime


class ProjectMembership(BaseModel):
    """A project the current user belongs to, with their role in it."""

    project: Project
    role: ProjectRole


class Member(BaseModel):
    """A row in `/projects/{id}/members` — project_members joined with profile."""

    user_id: str
    role: ProjectRole
    joined_at: datetime
    email: str | None
    full_name: str | None
    avatar_url: str | None


class MemberCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    role: ProjectRole = "editor"


class MemberRoleUpdate(BaseModel):
    role: ProjectRole
