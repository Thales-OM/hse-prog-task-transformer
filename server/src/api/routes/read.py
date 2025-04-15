from fastapi import APIRouter, Depends, status, Body
from fastapi.exceptions import HTTPException
from psycopg2.extensions import cursor
from typing import List, Tuple
from src.logger import LoggerFactory
from src.config import settings
from src.utils import validate_xml
from src.api.deps import get_db_cursor
from src.schemas import GetQuestionResponse, QuestionsRandomIdResponse, Question, GetModelResponse, GetInferenceResponse, GetInferenceScoreResponse
from src.core import ingest_quiz_xml
from src.database.crud import get_questions_all, get_question, get_random_question_id, get_models_all, get_inference, get_inference_scores_all


logger = LoggerFactory.getLogger(__name__)


router = APIRouter(
    tags=["read"],
    prefix=""
)


@router.get(
    "/questions/all",
    response_model=List[GetQuestionResponse],
    status_code=status.HTTP_200_OK,
    summary="Fetch all questions from database",
    description="Construct question objects from all non-deleted questions and their answers/test cases",
)
async def questions_all(cursor: cursor = Depends(get_db_cursor)):
    questions = await get_questions_all(cursor=cursor)
    return questions


@router.get(
    "/question/{id}",
    response_model=GetQuestionResponse,
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


@router.get(
    "/models/all",
    response_model=List[GetModelResponse],
    status_code=status.HTTP_200_OK,
    summary="Fetch all models from database",
    description="Return full info (id, name etc) on all non-deleted models in database",
)
async def models_all(cursor: cursor = Depends(get_db_cursor)):
    models = await get_models_all(cursor=cursor)
    return models


@router.get(
    "/inference/{id}",
    response_model=GetInferenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch inference from database by ID",
)
async def inference(id: int, cursor: cursor = Depends(get_db_cursor)):
    inference = await get_inference(id=id, cursor=cursor)
    if inference is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inference was not found: wrong ID or was deleted")
    return inference


@router.get(
    "/inferences/scores/all",
    response_model=List[GetInferenceScoreResponse],
    status_code=status.HTTP_200_OK,
    summary="Fetch all non-deleted inference scores from database",
)
async def inferences_scores_all(cursor: cursor = Depends(get_db_cursor)):
    return await get_inference_scores_all(cursor=cursor)