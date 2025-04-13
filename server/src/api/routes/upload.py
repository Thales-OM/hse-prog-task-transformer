from fastapi import APIRouter, Depends, status, Body
from psycopg2.extensions import cursor
from src.logger import LoggerFactory
from src.config import settings
from src.utils import validate_xml
from src.api.deps import get_db_cursor
from src.schemas import MessageSuccessResponse
from src.core import ingest_quiz_xml


logger = LoggerFactory.getLogger(__name__)


router = APIRouter(
    tags=["upload"],
    prefix=""
)

@router.post(
    "/quiz/xml",
    response_model=MessageSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload quiz into database",
    description="Accepts an .xml file. Parses quiestions, answers etc and updates database",
)
async def quiz_xml(xml_data: str = Body(..., media_type="application/xml"), cursor: cursor = Depends(get_db_cursor)):
    validate_xml(data=xml_data)
    await ingest_quiz_xml(xml_contents=xml_data, cursor=cursor)
    return MessageSuccessResponse(message="File processed successfully")