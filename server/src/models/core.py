from typing import List, Optional
import re
from psycopg2.extensions import cursor
from typing import List
from openai import AsyncClient
from openai.types.chat import ChatCompletion
import string
import json
import pandas as pd
from src.models.constraints import (
    PROMPT_TEMPLATE_MULTICHOICE,
    PROMPT_TEMPLATE_CODERUNNER,
    PROMPT_TEMPLATE_OTHER,
    DEFAULT_MODEL_TEMPERATURE,
)
from src.constraints import (
    QUESTION_MULTICHOICE_TYPES,
    QUESTION_CODERUNNER_TYPES,
    QUESTION_CLOZE_TYPES,
)
from src.schemas import Question, ReasoningLLModelResponse, GetPromptResponse
from src.database.crud import (
    get_model,
    get_question,
    create_inference,
    get_question_admin,
    get_questions_all_admin,
    get_inference,
    get_scores_for_inference,
)


class PromptBuilder:
    prompt_template_multichoice: str = PROMPT_TEMPLATE_MULTICHOICE
    prompt_template_coderunner: str = PROMPT_TEMPLATE_CODERUNNER
    prompt_template_other: str = PROMPT_TEMPLATE_OTHER

    @staticmethod
    def build(question: Question) -> str:
        if question.type in QUESTION_MULTICHOICE_TYPES:
            return PromptBuilder.build_multichoice(question=question)
        if question.type in QUESTION_CODERUNNER_TYPES:
            return PromptBuilder.build_coderunner(question=question)
        return PromptBuilder.build_other(question=question)

    @classmethod
    def build_multichoice(cls, question: Question) -> str:
        if question.type not in QUESTION_MULTICHOICE_TYPES:
            raise ValueError(
                f"Question of type '{question.type}' wrongly passeed to Multichoice prompt build method"
            )
        all_answers = [answer.text for answer in question.answers]
        correct_answers = [
            answer.text for answer in question.answers if answer.is_correct
        ]
        return cls.prompt_template_multichoice.format(
            task_type=question.type,
            task_text=question.text,
            all_answers=all_answers,
            correct_answers=correct_answers,
        )

    @classmethod
    def build_coderunner(cls, question: Question) -> str:
        if question.type not in QUESTION_CODERUNNER_TYPES:
            raise ValueError(
                f"Question of type '{question.type}' wrongly passeed to Coderunner prompt build method"
            )
        correct_answers = [
            answer.text for answer in question.answers
        ]  # Coderunner only contains correct answers
        test_cases = [
            f"[{idx+1}] Входные данные:\n{test_case.input}\nОжидаемый вывод:\n{test_case.expected_output}\n\n"
            for idx, test_case in enumerate(question.test_cases)
        ]
        return cls.prompt_template_coderunner.format(
            task_type=question.type,
            task_text=question.text,
            correct_answers=correct_answers,
            test_cases=test_cases,
        )

    @classmethod
    def build_other(cls, question: Question) -> str:
        if question.type in QUESTION_MULTICHOICE_TYPES:
            raise ValueError(
                f"Question of type '{question.type}' wrongly passeed to Other prompt build method. Must be passed to Multichoice builder."
            )
        if question.type in QUESTION_CODERUNNER_TYPES:
            raise ValueError(
                f"Question of type '{question.type}' wrongly passeed to Other prompt build method. Must be passed to Coderunner builder."
            )
        return cls.prompt_template_other.format(
            task_type=question.type, task_text=question.text
        )


def construct_messages(question: Question) -> List[dict]:
    return [
        {
            "role": "system",
            "content": "Ты опытный преподаватель Python для студентов гуманитарных специальностей",
        },
        {"role": "user", "content": PromptBuilder.build(question=question)},
    ]


async def get_completion(
    client: AsyncClient,
    model: str,
    messages: List[dict],
    temperature: float = DEFAULT_MODEL_TEMPERATURE,
) -> ChatCompletion:
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response


async def make_prompt(question_id: int, cursor: cursor) -> GetPromptResponse:
    question = await get_question_admin(id=question_id, cursor=cursor)
    messages = construct_messages(question=question)
    return GetPromptResponse(messages=messages, prompt=messages[1]["content"])


async def make_inference(
    client: AsyncClient,
    model_id: int,
    question_id: int,
    cursor: cursor,
    temperature: float = DEFAULT_MODEL_TEMPERATURE,
) -> int:
    model = await get_model(id=model_id, cursor=cursor)
    question = await get_question_admin(id=question_id, cursor=cursor)
    messages = construct_messages(question=question)
    completion = await get_completion(
        client=client,
        model=model.model_name,
        messages=messages,
        temperature=temperature,
    )
    model_response = ReasoningLLModelResponse.from_completion(
        completion=completion, temperature=temperature
    )
    return await create_inference(
        question_id=question_id,
        model_id=model_id,
        inference=model_response,
        cursor=cursor,
    )


async def build_report_df(cursor: cursor) -> pd.DataFrame:
    all_questions_in_db = await get_questions_all_admin(cursor=cursor)
    data = []
    for question in all_questions_in_db:
        messages = construct_messages(question=question)
        prompt = PromptBuilder.build(question=question)
        for inference_id in question.inference_ids:
            inference = await get_inference(id=inference_id, cursor=cursor)
            model = await get_model(id=inference.model_id, cursor=cursor)
            scores = await get_scores_for_inference(
                inference_id=inference.id, cursor=cursor
            )
            for score in scores:
                data.append(
                    {
                        "base_model_name": model.base_model_name,
                        "model_version": model.version,
                        "user_group_cd": score.user_group_cd,
                        "messages": json.dumps(messages),
                        "prompt_id": question.id,
                        "prompt": prompt,
                        "response_id": inference.id,
                        "response": inference.text,
                        "helpful": score.helpful,
                        "does_not_reveal_answer": score.does_not_reveal_answer,
                        "does_not_contain_errors": (score.does_not_contain_errors > 1),
                        "only_relevant_info": score.only_relevant_info,
                    }
                )
    return pd.DataFrame(data)


async def build_dataset_df(
    cursor: cursor, question_ids: Optional[List[int]] = None
) -> pd.DataFrame:
    if question_ids is None:
        questions = await get_questions_all_admin(cursor=cursor)
    else:
        questions = [
            question
            for question_id in question_ids
            if (question := await get_question_admin(id=question_id, cursor=cursor))
            is not None
        ]

    data = []
    for question in questions:
        messages = construct_messages(question=question)
        prompt = PromptBuilder.build(question=question)
        data.append(
            {
                "messages": json.dumps(messages),
                "prompt_id": question.id,
                "prompt": prompt,
            }
        )
    return pd.DataFrame(data)
