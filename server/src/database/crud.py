from psycopg2.extensions import cursor
from typing import List, Optional, Tuple
from src.logger import LoggerFactory
from src.schemas import (
    Question,
    Answer,
    AnswerMultichoice,
    AnswerCoderunner,
    TestCase,
    GetQuestionResponse,
    GetModelResponse,
    PostModelRequest,
    ReasoningLLModelResponse,
    GetInferenceResponse,
)
from src.exceptions import AnswerMismatchException
from src.constraints import QUESTION_MULTICHOICE_TYPES, QUESTION_CODERUNNER_TYPES


logger = LoggerFactory.getLogger(__name__)


async def update_db_state(question: Question, cursor: cursor) -> None:
    question_id = await create_question(question=question, cursor=cursor)
    for answer in question.answers:
        await create_answer(question_id=question_id, answer=answer, cursor=cursor)
    for test_case in question.test_cases:
        await create_test_case(question_id=question_id, test_case=test_case, cursor=cursor)


async def create_question(
    question: Question, cursor: cursor
) -> int:
    """Retrieve ID of the target question (insert/update question if needed)"""
    upsert_query = """
        INSERT INTO prod_storage.questions (name, type, text)
        VALUES (%(name)s, %(type)s, %(text)s)
        ON CONFLICT ON CONSTRAINT questions_source_key_unique DO UPDATE
        SET 
            type = EXCLUDED.type,
            text = EXCLUDED.text,
            updated_at = CURRENT_TIMESTAMP,
            deleted_flg = false
        RETURNING id
        ;
    """
    cursor.execute(upsert_query, question.model_dump(include={"name", "type", "text"}))
    question_id = cursor.fetchone()[0]
    return question_id


async def create_answer(question_id: int, answer: Answer, cursor: cursor) -> None:
    """Route Answer object into appropriate create method"""
    if isinstance(answer, AnswerMultichoice):
        await create_answer_multichoice(question_id=question_id, answer=answer, cursor=cursor)
        return
    elif isinstance(answer, AnswerCoderunner):
        await create_answer_coderunner(question_id=question_id, answer=answer, cursor=cursor)
        return
    raise AnswerMismatchException("Unrecognized Answer type received by database")


async def create_answer_multichoice(
    question_id: int, answer: AnswerMultichoice, cursor: cursor
) -> None:
    """Create answer record of multichoice type (update if exists)"""
    upsert_query = """
        INSERT INTO prod_storage.answers_multichoice (question_id, text, is_correct, fraction)
        VALUES (%(question_id)s, %(text)s, %(is_correct)s, %(fraction)s)
        ON CONFLICT ON CONSTRAINT answers_multichoice_source_key_unique DO UPDATE
        SET 
            is_correct = EXCLUDED.is_correct,
            fraction = EXCLUDED.fraction,
            updated_at = CURRENT_TIMESTAMP,
            deleted_flg = false
        RETURNING id
        ;
    """
    data = answer.model_dump(include={"text", "is_correct", "fraction"})
    data["question_id"] = question_id
    cursor.execute(upsert_query, data)


async def create_answer_coderunner(
    question_id: int, answer: AnswerCoderunner, cursor: cursor
) -> None:
    """Create answer record of coderunner type (update if exists)"""
    upsert_query = """
        INSERT INTO prod_storage.answers_coderunner (question_id, text)
        VALUES (%(question_id)s, %(text)s)
        ON CONFLICT ON CONSTRAINT answers_coderunner_source_key_unique DO UPDATE
        SET 
            updated_at = CURRENT_TIMESTAMP,
            deleted_flg = false
        RETURNING id
        ;
    """
    data = answer.model_dump(include={"text"})
    data["question_id"] = question_id
    cursor.execute(upsert_query, data)


async def create_test_case(
    question_id: int, test_case: TestCase, cursor: cursor
) -> None:
    """Create test case record for question (update if exists)"""
    upsert_query = """
        INSERT INTO prod_storage.test_cases (question_id, code, input, expected_output, example)
        VALUES (%(question_id)s, %(code)s, %(input)s, %(expected_output)s, %(example)s)
        ON CONFLICT ON CONSTRAINT test_cases_source_key_unique DO UPDATE
        SET 
            code = EXCLUDED.code,
            expected_output = EXCLUDED.expected_output,
            example = EXCLUDED.example,
            updated_at = CURRENT_TIMESTAMP,
            deleted_flg = false
        RETURNING id
        ;
    """
    data = test_case.model_dump(include={"code", "input", "expected_output", "example"})
    data["question_id"] = question_id
    cursor.execute(upsert_query, data)


async def get_questions_all(cursor: cursor) -> List[GetQuestionResponse]:
    """Get all not soft-deleted questions in database"""
    select_query = "SELECT id, name, type, text FROM prod_storage.questions WHERE deleted_flg = false;"
    cursor.execute(select_query)
    question_records = cursor.fetchall()
    questions = []
    for question_record in question_records:
        id, name, _type, text = question_record
        answers = []
        test_cases = []
        if _type in QUESTION_MULTICHOICE_TYPES:
            answers = await get_answers_multichoice(question_id=id, cursor=cursor)
        elif _type in QUESTION_CODERUNNER_TYPES:
            answers = await get_answers_coderunner(question_id=id, cursor=cursor)
            test_cases = await get_test_cases(question_id=id, cursor=cursor)
        
        inference_ids = await get_question_inference_ids(question_id=id, cursor=cursor)
        
        questions.append(GetQuestionResponse(id=id, name=name, type=_type, text=text, answers=answers, test_cases=test_cases, inference_ids=inference_ids))
    return questions


async def get_question(id: int, cursor: cursor) -> Optional[GetQuestionResponse]:
    select_query = "SELECT id, name, type, text FROM prod_storage.questions WHERE id = %s AND deleted_flg = false;"
    cursor.execute(select_query, (id,))
    question_record = cursor.fetchone()
    if question_record is None:
        return None
    
    id, name, _type, text = question_record
    answers = []
    test_cases = []
    if _type in QUESTION_MULTICHOICE_TYPES:
        answers = await get_answers_multichoice(question_id=id, cursor=cursor)
    elif _type in QUESTION_CODERUNNER_TYPES:
        answers = await get_answers_coderunner(question_id=id, cursor=cursor)
        test_cases = await get_test_cases(question_id=id, cursor=cursor)
    
    inference_ids = await get_question_inference_ids(question_id=id, cursor=cursor)

    return GetQuestionResponse(id=id, name=name, type=_type, text=text, answers=answers, test_cases=test_cases, inference_ids=inference_ids)


async def get_answers_multichoice(question_id: int, cursor: cursor) -> List[AnswerMultichoice]:
    select_query = """
        SELECT 
            text, is_correct, fraction
        FROM
            prod_storage.answers_multichoice  
        WHERE
            question_id = %s
            AND deleted_flg = false
        ;
    """
    cursor.execute(select_query, (question_id,))
    answer_records = cursor.fetchall()
    return [AnswerMultichoice(text=text, is_correct=is_correct, fraction=fraction) for text, is_correct, fraction in answer_records]


async def get_answers_coderunner(question_id: int, cursor: cursor) -> List[AnswerCoderunner]:
    select_query = """
        SELECT 
            text
        FROM
            prod_storage.answers_coderunner 
        WHERE
            question_id = %s
            AND deleted_flg = false
        ;
    """
    cursor.execute(select_query, (question_id,))
    answer_records = cursor.fetchall()
    return [AnswerCoderunner(text=record[0]) for record in answer_records] 


async def get_test_cases(question_id: int, cursor: cursor) -> List[TestCase]:
    select_query = """
        SELECT 
            code, input, expected_output, example
        FROM
            prod_storage.test_cases
        WHERE
            question_id = %s
            AND deleted_flg = false
        ;
    """
    cursor.execute(select_query, (question_id,))
    test_case_records = cursor.fetchall()
    return [TestCase(code=code, input=input, expected_output=expected_output, example=example) for code, input, expected_output, example in test_case_records]


async def get_random_question_id(cursor: cursor) -> Optional[int]:
    select_query = "SELECT id FROM prod_storage.questions WHERE deleted_flg = false ORDER BY RANDOM() LIMIT 1;"
    cursor.execute(select_query,)
    question_record = cursor.fetchone()
    if question_record is None:
        return None
    return question_record[0]


async def create_model(model: PostModelRequest, cursor: cursor) -> int:
    upsert_query = """
        INSERT INTO prod_storage.models (base_model_name, model_name, version)
        VALUES (%(base_model_name)s, %(model_name)s, (SELECT COALESCE(MAX(version), -1) + 1 FROM prod_storage.models WHERE base_model_name = %(base_model_name)s))
        ON CONFLICT ON CONSTRAINT models_source_key_unique DO UPDATE
        SET 
            model_name = %(model_name)s,
            updated_at = CURRENT_TIMESTAMP,
            deleted_flg = false
        RETURNING id
        ;
    """
    cursor.execute(upsert_query, model.model_dump(include={"base_model_name", "model_name"}))
    model_id = cursor.fetchone()[0]
    return model_id


async def get_models_all(cursor: cursor) -> List[GetModelResponse]:
    select_query = "SELECT id, base_model_name, model_name, version FROM prod_storage.models WHERE deleted_flg = false;"
    cursor.execute(select_query)
    model_records = cursor.fetchall()
    models = []
    return [GetModelResponse(id=id, base_model_name=base_model_name, model_name=model_name, version=version) for id, base_model_name, model_name, version in model_records]


async def get_model(id: int, cursor: cursor) -> Optional[GetModelResponse]:
    select_query = "SELECT id, base_model_name, model_name, version FROM prod_storage.models WHERE id = %s AND deleted_flg = false;"
    cursor.execute(select_query, (id,))
    model_record = cursor.fetchone()
    if model_record is None:
        return None
    id, base_model_name, model_name, version = model_record
    return GetModelResponse(id=id, base_model_name=base_model_name, model_name=model_name, version=version)


async def create_inference(question_id: int, model_id: int, inference: ReasoningLLModelResponse, cursor: cursor) -> int:
    insert_query = """
        INSERT INTO prod_storage.questions_transformed
            (question_id, model_id, thinking, text)
        VALUES
            (%(question_id)s, %(model_id)s, %(reasoning)s, %(response)s)
        RETURNING id
        ;
    """
    data = inference.model_dump(include={"reasoning", "response"})
    data["question_id"] = question_id
    data["model_id"] = model_id
    cursor.execute(insert_query, data)
    inference_id = cursor.fetchone()[0]
    return inference_id


async def get_inference(id: int, cursor: cursor) -> Optional[GetInferenceResponse]:
    select_query = "SELECT id, question_id, model_id, thinking, text FROM prod_storage.questions_transformed WHERE id = %s AND deleted_flg = false;"
    cursor.execute(select_query, (id,))
    record = cursor.fetchone()
    if record is None:
        return None
    id, question_id, model_id, thinking, text = record
    return GetInferenceResponse(id=id, question_id=question_id, model_id=model_id, thinking=thinking, text=text)


async def get_question_inference_ids(question_id: int, cursor: cursor) -> List[int]:
    select_query = "SELECT id FROM prod_storage.questions_transformed WHERE question_id = %s AND deleted_flg = false;"
    cursor.execute(select_query, (question_id,))
    return [record[0] for record in cursor.fetchall()]
