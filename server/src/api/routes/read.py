from fastapi import APIRouter, Depends, status, Body
from fastapi.exceptions import HTTPException
from psycopg2.extensions import cursor
from typing import List
from src.logger import LoggerFactory
from src.config import settings
from src.utils import validate_xml
from src.api.deps import get_db_cursor
from src.schemas import QuestionResponse, QuestionsRandomIdResponse
from src.core import ingest_quiz_xml
from src.database.crud import get_questions_all, get_question, get_random_question_id


logger = LoggerFactory.getLogger(__name__)


router = APIRouter(
    tags=["read"],
    prefix=""
)


@router.get(
    "/questions/all",
    response_model=List[QuestionResponse],
    status_code=status.HTTP_200_OK,
    summary="Fetch all questions from database",
    description="Construct question objects from all non-deleted questions and their answers/test cases",
)
async def questions_all(cursor: cursor = Depends(get_db_cursor)):
    questions = await get_questions_all(cursor=cursor)
    return questions


@router.get(
    "/question/{id}",
    response_model=QuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch a question from database by ID",
    description="Construct question object from non-deleted database record and its answers/test cases",
)
async def question(id: int, cursor: cursor = Depends(get_db_cursor)):
    question = await get_question(id=id, cursor=cursor)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question does not exist in database or was deleted")
    return question


@router.get(
    "/questions/random/id",
    response_model=QuestionsRandomIdResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch a random question ID from database",
)
async def questions_random_id(cursor: cursor = Depends(get_db_cursor)):
    id = await get_random_question_id(cursor=cursor)
    if id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empty Question ID was received: database error or empty")
    return QuestionsRandomIdResponse(id=id)
