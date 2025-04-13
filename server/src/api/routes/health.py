from fastapi import APIRouter, Depends, status, Body
from src.logger import LoggerFactory
from src.config import settings
from src.schemas import MessageSuccessResponse


logger = LoggerFactory.getLogger(__name__)


router = APIRouter(
    tags=["health"],
    prefix=""
)

@router.get(
    "",
    response_model=MessageSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Simple server health check",
    description="Send GET request to this endpoint to check server health status (OK or not)",
)
async def root():
    return MessageSuccessResponse(message="Ok")