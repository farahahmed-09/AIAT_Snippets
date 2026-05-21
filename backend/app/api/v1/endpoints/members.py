from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep
from app.schemas.project import Member, MemberCreate, MemberRoleUpdate
from app.services import members

router = APIRouter()


@router.get("", response_model=list[Member])
def list_members(project_id: int, user: CurrentUserDep) -> list[Member]:
    return members.list_members(user.id, project_id)


@router.post("", response_model=Member, status_code=status.HTTP_201_CREATED)
def add_member(
    project_id: int, payload: MemberCreate, user: CurrentUserDep
) -> Member:
    return members.add_member(user.id, project_id, payload)


@router.patch("/{user_id}", response_model=Member)
def update_member_role(
    project_id: int,
    user_id: str,
    payload: MemberRoleUpdate,
    user: CurrentUserDep,
) -> Member:
    return members.update_role(user.id, project_id, user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(project_id: int, user_id: str, user: CurrentUserDep) -> None:
    members.remove_member(user.id, project_id, user_id)
