from fastapi import APIRouter, HTTPException, status

from deps import CurrentUserDep
from schemas.session import LessonData
from schemas.user import DashboardData

router = APIRouter()

_NOT_IMPLEMENTED = HTTPException(
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    detail="Not implemented",
)


@router.get("/memory", response_model=DashboardData)
def memory(_user: CurrentUserDep) -> DashboardData:
    raise _NOT_IMPLEMENTED


@router.get("/sessions", response_model=list[LessonData])
def sessions(_user: CurrentUserDep, page: int = 1) -> list[LessonData]:
    raise _NOT_IMPLEMENTED
