from typing import Annotated

from fastapi import Depends

from app.core.security import CurrentUser, get_current_user

CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
