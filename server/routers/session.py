from fastapi import APIRouter, HTTPException, Response, status

from deps import CurrentUserDep
from schemas.session import (
    LessonData,
    SessionAnswerRequest,
    SessionAnswerResponse,
    SessionEndRequest,
    SessionHintRequest,
    SessionHintResponse,
    SessionStartRequest,
    SessionStartResponse,
)

router = APIRouter()

_NOT_IMPLEMENTED = HTTPException(
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    detail="Not implemented",
)


@router.post("/start", response_model=SessionStartResponse)
def start(_body: SessionStartRequest, _user: CurrentUserDep) -> SessionStartResponse:
    raise _NOT_IMPLEMENTED


@router.post("/answer", response_model=SessionAnswerResponse)
def answer(_body: SessionAnswerRequest, _user: CurrentUserDep) -> SessionAnswerResponse:
    raise _NOT_IMPLEMENTED


@router.post("/hint", response_model=SessionHintResponse)
def hint(_body: SessionHintRequest, _user: CurrentUserDep) -> SessionHintResponse:
    raise _NOT_IMPLEMENTED


@router.post("/end", status_code=status.HTTP_204_NO_CONTENT)
def end(_body: SessionEndRequest, _user: CurrentUserDep) -> Response:
    raise _NOT_IMPLEMENTED


@router.get("/{session_id}", response_model=LessonData)
def get_session(session_id: str, _user: CurrentUserDep) -> LessonData:
    raise _NOT_IMPLEMENTED
