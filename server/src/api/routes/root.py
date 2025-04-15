from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse
from src.logger import LoggerFactory
from src.config import settings


logger = LoggerFactory.getLogger(__name__)


router = APIRouter(
    prefix=""
)


# Root redirect
@router.get("/", response_class=RedirectResponse, status_code=status.HTTP_200_OK)
async def root():
    return RedirectResponse(url="/pages/main")