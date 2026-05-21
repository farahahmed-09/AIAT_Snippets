from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.deps import CurrentUserDep
from app.schemas.intro_asset import IntroAsset
from app.services import intro_assets

# Single-item operations live at /intro-assets/{id}.
router = APIRouter()


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_intro_asset(asset_id: int, user: CurrentUserDep) -> None:
    intro_assets.delete(user.id, asset_id)


# Project-scoped collection — mounted at /projects/{project_id}/intro-assets.
project_scoped_router = APIRouter()


@project_scoped_router.get("", response_model=list[IntroAsset])
def list_intros(project_id: int, user: CurrentUserDep) -> list[IntroAsset]:
    return intro_assets.list_for_project(user.id, project_id)


@project_scoped_router.post(
    "", response_model=IntroAsset, status_code=status.HTTP_201_CREATED
)
async def upload_intro(
    project_id: int,
    user: CurrentUserDep,
    name: str = Form(...),
    video: UploadFile = File(...),
    thumbnail: UploadFile | None = File(default=None),
) -> IntroAsset:
    return await intro_assets.create(user.id, project_id, name, video, thumbnail)
