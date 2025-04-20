# pages.py
from fastapi import APIRouter, Request, HTTPException, status, Path, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
import pathlib
import httpx
from src.config import settings
from src.constraints import KNOWN_QUESTION_TYPES, QUESTION_MULTICHOICE_TYPES, QUESTION_CODERUNNER_TYPES, QUESTION_CLOZE_TYPES
from src.schemas import QuestionPageResponse, Question, GetQuestionResponse, GetInferenceResponse, QuestionInferencePageResponse, GetInferenceScoreResponse, LanguagePageResponse
from src.language import language_manager
from src.types import Language
from src.api.deps import get_language_query


BACKEND_URL = settings.server.url


router = APIRouter(
    tags=["pages"],
    prefix=""
)


ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent.parent
templates = Jinja2Templates(directory=str(ROOT_DIR / "templates"))


@router.get("/{user_group_cd}/questions/list", response_class=HTMLResponse, status_code=status.HTTP_200_OK)
async def list_questions(request: Request, user_group_cd: str = Path(...), lang: Language = Depends(get_language_query)):
    try:
        async with httpx.AsyncClient() as client:
            params = {"user_group_cd": user_group_cd}
            response = await client.get(f"{BACKEND_URL}/read/questions/all", params=params)
            response.raise_for_status()
            questions_list = response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch questions:\n{e}")

    questions = [QuestionPageResponse.from_question_response(question_response=GetQuestionResponse(**question)) for question in questions_list]

    return templates.TemplateResponse(
        "question_list.html",
        {"request": request, "questions": questions, "user_group_cd": user_group_cd, "languages": LanguagePageResponse(current=lang, pack=language_manager.get_language_pack(language=lang).question_list)}
    )


@router.get("/{user_group_cd}/question/{id}", response_class=HTMLResponse, status_code=status.HTTP_200_OK)
async def question_detail(request: Request, user_group_cd: str = Path(...), id: int = Path(...), lang: Language = Depends(get_language_query)):
    try:
        async with httpx.AsyncClient() as client:
            params = {"user_group_cd": user_group_cd}
            response = await client.get(f"{BACKEND_URL}/read/question/{id}", params=params)
            response.raise_for_status()
            question_json = response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch question {id}:\n{e}")
    
    question_obj = GetQuestionResponse(**question_json)
    question_page_response = QuestionPageResponse.from_question_response(question_response=question_obj)

    return templates.TemplateResponse(
        "question_detail.html",
        {"request": request, "question": question_page_response, "user_group_cd": user_group_cd, "languages": LanguagePageResponse(current=lang, pack=language_manager.get_language_pack(language=lang).question)}
    )


@router.get("/{user_group_cd}/questions/random", response_class=RedirectResponse, status_code=status.HTTP_200_OK)
async def questions_random(request: Request, user_group_cd: str = Path(...)):
    try:
        async with httpx.AsyncClient() as client:
            params = {"user_group_cd": user_group_cd}
            response = await client.get(f"{BACKEND_URL}/read/questions/random/id", params=params)
            response.raise_for_status()
            question_id = response.json()["id"]
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch question ID:\n{e}")
    
    return RedirectResponse(url=f"/pages/{user_group_cd}/question/{question_id}")


@router.get("/{user_group_cd}/questions/inference/{id}", response_class=HTMLResponse, status_code=status.HTTP_200_OK)
async def question_inference(request: Request, user_group_cd: str = Path(...), id: int = Path(...), lang: Language = Depends(get_language_query)):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/read/inference/{id}")
            response.raise_for_status()
            inference_json = response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch inference ID {id}:\n{e}")
    
    inference = GetInferenceResponse(**inference_json)

    try:
        async with httpx.AsyncClient() as client:
            params = {"user_group_cd": user_group_cd}
            response = await client.get(f"{BACKEND_URL}/read/question/{inference.question_id}", params=params)
            response.raise_for_status()
            question_json = response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch question ID {inference.question_id}:\n{e}")

    question = GetQuestionResponse(**question_json)
    question_page_response = QuestionInferencePageResponse.from_question_response(question_response=question, inference=inference)

    return templates.TemplateResponse(
        "question_inference.html",
        {"request": request, "question": question_page_response, "user_group_cd": user_group_cd, "languages": LanguagePageResponse(current=lang, pack=language_manager.get_language_pack(language=lang).inference)}
    )


@router.get("/{user_group_cd}/inferences/scores/list", response_class=HTMLResponse, status_code=status.HTTP_200_OK)
async def question_detail(request: Request, user_group_cd: str = Path(...), lang: Language = Depends(get_language_query)):
    try:
        async with httpx.AsyncClient() as client:
            params = {"user_group_cd": user_group_cd}
            response = await client.get(f"{BACKEND_URL}/read/inferences/scores/all", params=params)
            response.raise_for_status()
            scores_json = response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch scores")
    
    scores_page_response = [GetInferenceScoreResponse(**score) for score in scores_json]

    return templates.TemplateResponse(
        "inference_score_list.html",
        {"request": request, "scores": scores_page_response, "user_group_cd": user_group_cd, "languages": LanguagePageResponse(current=lang, pack=language_manager.get_language_pack(language=lang).score_list)}
    )


@router.get("/{user_group_cd}/dashboard", response_class=HTMLResponse, status_code=status.HTTP_200_OK)
async def dashboard(request: Request, user_group_cd: str = Path(...), lang: Language = Depends(get_language_query)):
    try:
        async with httpx.AsyncClient() as client:
            params = {"user_group_cd": user_group_cd}
            response = await client.get(f"{BACKEND_URL}/read/users/group/verify", params=params)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Invalid User Group path:\n{e}")
    
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user_group_cd": user_group_cd, "languages": LanguagePageResponse(current=lang, pack=language_manager.get_language_pack(language=lang).dashboard)}
    )


@router.get("/main", response_class=HTMLResponse, status_code=status.HTTP_200_OK)
async def main(request: Request, lang: Language = Depends(get_language_query)):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/read/users/groups/all")
            response.raise_for_status()
            user_groups = response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to retrieve User Groups:\n{e}")
    
    return templates.TemplateResponse(
        "main.html",
        {"request": request, "user_groups": user_groups, "languages": LanguagePageResponse(current=lang, pack=language_manager.get_language_pack(language=lang).main)}
    )
