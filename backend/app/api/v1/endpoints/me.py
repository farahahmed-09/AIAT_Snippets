from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentUserDep
from app.schemas.profile import Profile, ProfileUpdate
from app.schemas.project import ProjectMembership
from app.services import profiles, projects

router = APIRouter()


class MeResponse(BaseModel):
    profile: Profile
    memberships: list[ProjectMembership]


@router.get("", response_model=MeResponse)
def me(user: CurrentUserDep) -> MeResponse:
    return MeResponse(
        profile=profiles.get_profile(user.id),
        memberships=projects.list_for_user(user.id),
    )


@router.patch("", response_model=Profile)
def update_me(payload: ProfileUpdate, user: CurrentUserDep) -> Profile:
    return profiles.update_profile(user.id, payload)
