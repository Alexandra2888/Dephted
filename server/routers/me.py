from fastapi import APIRouter

from deps import CurrentUserDep
from schemas.auth import MeResponse

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUserDep) -> MeResponse:
    return MeResponse(user_id=user.user_id, email=user.email)
