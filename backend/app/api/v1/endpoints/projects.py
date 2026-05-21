from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep
from app.schemas.project import (
    Project,
    ProjectCreate,
    ProjectMembership,
    ProjectUpdate,
)
from app.services import projects

router = APIRouter()


@router.get("", response_model=list[ProjectMembership])
def list_my_projects(user: CurrentUserDep) -> list[ProjectMembership]:
    return projects.list_for_user(user.id)


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, user: CurrentUserDep) -> Project:
    return projects.create(user.id, payload)


@router.patch("/{project_id}", response_model=Project)
def update_project(
    project_id: int, payload: ProjectUpdate, user: CurrentUserDep
) -> Project:
    return projects.update(user.id, project_id, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, user: CurrentUserDep) -> None:
    projects.delete(user.id, project_id)
