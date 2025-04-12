from psycopg2.extensions import cursor
from src.logger import LoggerFactory
from src.schemas import (
    Question,
    Answer,
    AnswerMultichoice,
    AnswerCoderunner,
    TestCase
)
from src.exceptions import AnswerMismatchException


logger = LoggerFactory.getLogger(__name__)


async def update_db_state(question: Question, cursor: cursor) -> None:
    question_id = await get_question(question=question, cursor=cursor)
    for answer in question.answers:
        await create_answer(question_id=question_id, answer=answer, cursor=cursor)
    for test_case in question.test_cases:
        await create_test_case(question_id=question_id, test_case=test_case, cursor=cursor)


async def get_question(
    question: Question, cursor: cursor
) -> int:
    """Retrieve ID of the target question (insert/update question if needed)"""
    upsert_query = """
        INSERT INTO prod_storage.questions (name, type, text)
        VALUES (%(name)s, %(type)s, %(text)s)
        ON CONFLICT (name) DO UPDATE
        SET 
            type = EXCLUDED.type,
            text = EXCLUDED.text,
            updated_at = CURRENT_TIMESTAMP,
            deleted_flg = false
        WHERE 
            questions.type <> EXCLUDED.type OR
            questions.text <> EXCLUDED.text OR
            questions.deleted_flg = true
        RETURNING id
        ;
    """
    cursor.execute(upsert_query, question.model_dump(include={"name", "type", "text"}))
    question_id = cursor.fetchone()[0]
    return question_id


async def create_answer(answer: Answer, cursor: cursor) -> None:
    """Route Answer object into appropriate create method"""
    if isinstance(answer, AnswerMultichoice):
        await create_answer_multichoice(answer=answer, cursor=cursor)
        return
    elif isinstance(answer, AnswerCoderunner):
        await create_answer_coderunner(answer=answer, cursor=cursor)
        return
    raise AnswerMismatchException("Unrecognized Answer type received by database")


async def create_answer_multichoice(
    question_id: int, answer: AnswerMultichoice, cursor: cursor
) -> None:
    """Create answer record of multichoice type (update if exists)"""
    upsert_query = """
        INSERT INTO prod_storage.answers_multichoice (question_id, text, is_correct, fraction)
        VALUES (%(question_id)s, %(text)s, %(is_correct)s, %(fraction)s)
        ON CONFLICT (question_id, text) DO UPDATE
        SET 
            is_correct = EXCLUDED.is_correct,
            fraction = EXCLUDED.fraction,
            updated_at = CURRENT_TIMESTAMP,
            deleted_flg = false
        WHERE 
            answers_multichoice.is_correct <> EXCLUDED.is_correct OR
            answers_multichoice.fraction <> EXCLUDED.fraction OR
            answers_multichoice.deleted_flg = true
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
        ON CONFLICT (question_id, text) DO UPDATE
        SET 
            updated_at = CURRENT_TIMESTAMP,
            deleted_flg = false
        WHERE 
            answers_coderunner.deleted_flg = true
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
        ON CONFLICT (question_id, input) DO UPDATE
        SET 
            code = EXCLUDED.code,
            expected_output = EXCLUDED.expected_output,
            example = EXCLUDED.example,
            updated_at = CURRENT_TIMESTAMP,
            deleted_flg = false
        WHERE 
            test_cases.code <> EXCLUDED.code OR
            test_cases.expected_output <> EXCLUDED.expected_output OR
            test_cases.example <> EXCLUDED.example OR
            test_cases.deleted_flg = true
        RETURNING id
        ;
    """
    data = test_case.model_dump(include={"text"})
    data["question_id"] = question_id
    cursor.execute(upsert_query, data)