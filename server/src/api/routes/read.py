from fastapi import APIRouter, Depends, status, Body, Path
from fastapi.exceptions import HTTPException
from fastapi.responses import StreamingResponse
from psycopg2.extensions import cursor
from io import StringIO
from typing import List, Tuple
from src.logger import LoggerFactory
from src.config import settings
from src.utils import validate_xml
from src.types import UserGroupCD
from src.api.deps import get_db_cursor, get_user_group_query
from src.schemas import (
    GetQuestionResponse,
    QuestionsRandomIdResponse,
    Question,
    GetModelResponse,
    GetInferenceResponse,
    GetInferenceScoreResponse,
    GetUserGroupResponse,
    MessageSuccessResponse,
    GetPromptResponse,
)
from src.core import ingest_quiz_xml
from src.database.crud import (
    get_questions_all,
    get_question,
    get_random_question_id,
    get_models_all,
    get_inference,
    get_inference_scores_all,
    get_user_groups_all,
)
from src.models.core import make_prompt, build_report_df


logger = LoggerFactory.getLogger(__name__)


router = APIRouter(tags=["read"], prefix="")


@router.get(
    "/questions/all",
    response_model=List[GetQuestionResponse],
    status_code=status.HTTP_200_OK,
    summary="Fetch all questions from database",
    description="Construct question objects from all non-deleted questions and their answers/test cases",
)
async def questions_all(
    user_group_cd: UserGroupCD = Depends(get_user_group_query),
    cursor: cursor = Depends(get_db_cursor),
):
    questions = await get_questions_all(user_group_cd=user_group_cd, cursor=cursor)
    return questions


@router.get(
    "/question/{id}",
    response_model=GetQuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch a question from database by ID",
    description="Construct question object from non-deleted database record and its answers/test cases",
)
async def question(
    id: int,
    user_group_cd: UserGroupCD = Depends(get_user_group_query),
    cursor: cursor = Depends(get_db_cursor),
):
    question = await get_question(user_group_cd=user_group_cd, id=id, cursor=cursor)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question does not exist in database or was deleted",
        )
    return question


@router.get(
    "/questions/random/id",
    response_model=QuestionsRandomIdResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch a random question ID from database",
)
async def questions_random_id(
    user_group_cd: UserGroupCD = Depends(get_user_group_query),
    cursor: cursor = Depends(get_db_cursor),
):
    id = await get_random_question_id(user_group_cd=user_group_cd, cursor=cursor)
    if id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empty Question ID was received: database error or empty",
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inference was not found: wrong ID or was deleted",
        )
    return inference


@router.get(
    "/inferences/scores/all",
    response_model=List[GetInferenceScoreResponse],
    status_code=status.HTTP_200_OK,
    summary="Fetch all non-deleted inference scores from database",
)
async def inferences_scores_all(
    user_group_cd: UserGroupCD = Depends(get_user_group_query),
    cursor: cursor = Depends(get_db_cursor),
):
    return await get_inference_scores_all(user_group_cd=user_group_cd, cursor=cursor)


@router.get(
    "/users/groups/all",
    response_model=List[GetUserGroupResponse],
    status_code=status.HTTP_200_OK,
    summary="Fetch all non-deleted User Groups from database",
)
async def users_groups_all(cursor: cursor = Depends(get_db_cursor)):
    return await get_user_groups_all(cursor=cursor)


@router.get(
    "/users/group/verify",
    response_model=MessageSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify that User Group is present in database",
)
async def users_groups_all(user_group_cd: UserGroupCD = Depends(get_user_group_query)):
    return MessageSuccessResponse(message="ok")


@router.get(
    "/prompts/question/{id}",
    response_model=GetPromptResponse,
    status_code=status.HTTP_200_OK,
    summary="Construct a ready prompt for a given question in database",
)
async def users_groups_all(
    id: int = Path(...), cursor: cursor = Depends(get_db_cursor)
):
    return await make_prompt(question_id=id, cursor=cursor)


@router.get(
    "/report/csv",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Get a full report on questions, inference, scores in a CSV file",
)
async def report_csv(cursor: cursor = Depends(get_db_cursor)):
    report_df = await build_report_df(cursor=cursor)
    csv_buffer = StringIO()
    report_df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return StreamingResponse(csv_buffer, media_type='text/csv', headers={"Content-Disposition": f"attachment; filename={settings.server.filenames.report_csv}"})
