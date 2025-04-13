# pages.py
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import httpx
from src.config import settings
from src.constraints import KNOWN_QUESTION_TYPES, QUESTION_MULTICHOICE_TYPES, QUESTION_CODERUNNER_TYPES, QUESTION_CLOZE_TYPES
from src.schemas import QuestionPageResponse, Question


BACKEND_URL = settings.server.url


router = APIRouter(
    prefix=""
)


ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
templates = Jinja2Templates(directory=str(ROOT_DIR / "templates"))


@router.get("/questions/list", response_class=HTMLResponse, status_code=status.HTTP_200_OK)
async def list_questions(request: Request):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/read/questions/all")
            response.raise_for_status()
            questions_list = response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Failed to fetch questions")

    questions = [QuestionPageResponse.from_question(id=id, question=Question(**question)) for id, question in questions_list]

    return templates.TemplateResponse(
        "question_list.html",
        {"request": request, "questions": questions}
    )

@router.get("/question/{id}", response_class=HTMLResponse, status_code=status.HTTP_200_OK)
async def question_detail(request: Request, id: int):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/read/question/{id}")
            response.raise_for_status()
            question_json = response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch question {id}")
    
    question_obj = Question(**question_json)
    question_page_response = QuestionPageResponse.from_question(id=id, question=question_obj)

    return templates.TemplateResponse(
        "question_detail.html",
        {"request": request, "question": question_page_response}
    )


@router.get("/questions/random", response_class=HTMLResponse, status_code=status.HTTP_200_OK)
async def questions_random(request: Request):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BACKEND_URL}/read/questions/random/id")
            response.raise_for_status()
            question_id = response.json()["id"]
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch question {question_id}")
    
    return RedirectResponse(url=f"/pages/question/{question_id}")
