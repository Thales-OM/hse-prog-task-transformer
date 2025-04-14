from fastapi import APIRouter, Depends, status, Body
from psycopg2.extensions import cursor
from openai import AsyncClient
from typing import List
from src.logger import LoggerFactory
from src.config import settings
from src.utils import validate_xml
from src.api.deps import get_db_cursor, get_openai_client
from src.schemas import MessageSuccessResponse, PostModelRequest, PostInferenceRequest
from src.core import ingest_quiz_xml
from src.database.crud import create_model
from src.models.core import make_inference


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


@router.post(
    "/models/new",
    response_model=MessageSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload new model specification",
)
async def models_new(body: PostModelRequest, cursor: cursor = Depends(get_db_cursor)):
    await create_model(model=body, cursor=cursor)
    return MessageSuccessResponse(message="Model created/updated successfully")


@router.post(
    "/inference/new",
    response_model=MessageSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new AI inference based on question text using a chosen model",
)
async def inference_new(body: PostInferenceRequest, openai_client: AsyncClient = Depends(get_openai_client), cursor: cursor = Depends(get_db_cursor)):
    await make_inference(client=openai_client, model_id=body.model_id, question_id=body.question_id, cursor=cursor, temperature=body.temperature)
    return MessageSuccessResponse(message="Inference created successfully")


@router.post(
    "/inferences/new",
    response_model=MessageSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create several new AI inferences based on question texts using a chosen models",
)
async def inferences_new(body: List[PostInferenceRequest], openai_client: AsyncClient = Depends(get_openai_client), cursor: cursor = Depends(get_db_cursor)):
    for inference_request in body:
        await make_inference(client=openai_client, model_id=inference_request.model_id, question_id=inference_request.question_id, cursor=cursor, temperature=inference_request.temperature)
    return MessageSuccessResponse(message="All Inferences created successfully")