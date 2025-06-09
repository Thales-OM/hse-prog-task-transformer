from psycopg2.extensions import cursor
from typing import List, Optional, Literal
import datetime
from src.logger import LoggerFactory
from src.types import UserGroupCD
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
    PostInferenceScoreRequest,
    GetInferenceScoreResponse,
    QuestionLevel,
    PostUserGroupRequest,
    PostUserGroupLevelAddRequest,
    PostSetUserGroupLevelRequest,
    UserGroup,
    LLModelResponse,
)
from src.exceptions import AnswerMismatchException, UnauthorizedException
from src.constraints import (
    QUESTION_MULTICHOICE_TYPES,
    QUESTION_CODERUNNER_TYPES,
    QUESTION_CLOZE_TYPES,
)
from src.utils import replace_and_append_options


logger = LoggerFactory.getLogger(__name__)


async def update_db_state(question: Question, cursor: cursor) -> int:
    question_id = await create_question(question=question, cursor=cursor)
    for answer in question.answers:
        await create_answer(question_id=question_id, answer=answer, cursor=cursor)
    for test_case in question.test_cases:
        await create_test_case(
            question_id=question_id, test_case=test_case, cursor=cursor
        )
    return question_id


async def create_question(question: Question, cursor: cursor) -> int:
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
        await create_answer_multichoice(
            question_id=question_id, answer=answer, cursor=cursor
        )
        return
    elif isinstance(answer, AnswerCoderunner):
        await create_answer_coderunner(
            question_id=question_id, answer=answer, cursor=cursor
        )
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


async def get_questions_all(
    user_group_cd: UserGroupCD, cursor: cursor
) -> List[GetQuestionResponse]:
    """Get all not soft-deleted questions in database"""
    select_query = """
        SELECT 
            q.id, q.name, q.type, q.text 
        FROM 
            (SELECT * FROM prod_storage.questions WHERE deleted_flg = false) q
            INNER JOIN (SELECT * FROM prod_storage.link_user_group_x_level WHERE user_group_cd = %s) link
                ON q.level_cd = link.level_cd
            ;
    """
    cursor.execute(select_query, (user_group_cd,))

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
        elif _type in QUESTION_CLOZE_TYPES:
            text = replace_and_append_options(text=text)

        inference_ids = await get_question_inference_ids(question_id=id, cursor=cursor)

        questions.append(
            GetQuestionResponse(
                id=id,
                name=name,
                type=_type,
                text=text,
                answers=answers,
                test_cases=test_cases,
                inference_ids=inference_ids,
            )
        )
    return questions


async def get_question(
    user_group_cd: UserGroupCD, id: int, cursor: cursor
) -> Optional[GetQuestionResponse]:
    select_query = """
        SELECT 
            q.id, q.name, q.type, q.text, (link.level_cd is not NULL) as allowed_flg 
        FROM 
            (SELECT * FROM prod_storage.questions WHERE id = %s AND deleted_flg = false) q
            LEFT JOIN (SELECT * FROM prod_storage.link_user_group_x_level WHERE user_group_cd= %s) link
                ON q.level_cd = link.level_cd
        ;
    """
    cursor.execute(select_query, (id, user_group_cd))
    question_record = cursor.fetchone()
    if question_record is None:
        return None

    id, name, _type, text, allowed_flg = question_record

    if not allowed_flg:
        raise UnauthorizedException(
            f'User Group "{user_group_cd}" is not allowed to access Question ID {id}'
        )

    answers = []
    test_cases = []
    if _type in QUESTION_MULTICHOICE_TYPES:
        answers = await get_answers_multichoice(question_id=id, cursor=cursor)
    elif _type in QUESTION_CODERUNNER_TYPES:
        answers = await get_answers_coderunner(question_id=id, cursor=cursor)
        test_cases = await get_test_cases(question_id=id, cursor=cursor)
    elif _type in QUESTION_CLOZE_TYPES:
        text = replace_and_append_options(text=text)

    inference_ids = await get_question_inference_ids(question_id=id, cursor=cursor)

    return GetQuestionResponse(
        id=id,
        name=name,
        type=_type,
        text=text,
        answers=answers,
        test_cases=test_cases,
        inference_ids=inference_ids,
    )


async def get_question_admin(id: int, cursor: cursor) -> Optional[GetQuestionResponse]:
    select_query = """
        SELECT 
            id, name, type, text 
        FROM 
            prod_storage.questions 
        WHERE 
            id = %s 
            AND deleted_flg = false
        ;
    """
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
    elif _type in QUESTION_CLOZE_TYPES:
        text = replace_and_append_options(text=text)

    inference_ids = await get_question_inference_ids(question_id=id, cursor=cursor)

    return GetQuestionResponse(
        id=id,
        name=name,
        type=_type,
        text=text,
        answers=answers,
        test_cases=test_cases,
        inference_ids=inference_ids,
    )


async def get_answers_multichoice(
    question_id: int, cursor: cursor
) -> List[AnswerMultichoice]:
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
    return [
        AnswerMultichoice(text=text, is_correct=is_correct, fraction=fraction)
        for text, is_correct, fraction in answer_records
    ]


async def get_answers_coderunner(
    question_id: int, cursor: cursor
) -> List[AnswerCoderunner]:
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
    return [
        TestCase(
            code=code, input=input, expected_output=expected_output, example=example
        )
        for code, input, expected_output, example in test_case_records
    ]


async def get_random_question_id(
    user_group_cd: UserGroupCD, cursor: cursor
) -> Optional[int]:
    select_query = """
        SELECT 
            q.id 
        FROM 
            (SELECT * FROM prod_storage.questions WHERE deleted_flg = false) q
            INNER JOIN (SELECT * FROM prod_storage.link_user_group_x_level WHERE user_group_cd= %s) link
                ON q.level_cd = link.level_cd
        ORDER BY 
            RANDOM() 
        LIMIT 1
        ;
    """
    cursor.execute(select_query, (user_group_cd,))
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
    cursor.execute(
        upsert_query, model.model_dump(include={"base_model_name", "model_name"})
    )
    model_id = cursor.fetchone()[0]
    return model_id


async def get_models_all(cursor: cursor) -> List[GetModelResponse]:
    select_query = "SELECT id, base_model_name, model_name, version FROM prod_storage.models WHERE deleted_flg = false;"
    cursor.execute(select_query)
    model_records = cursor.fetchall()
    models = []
    return [
        GetModelResponse(
            id=id,
            base_model_name=base_model_name,
            model_name=model_name,
            version=version,
        )
        for id, base_model_name, model_name, version in model_records
    ]


async def get_model(id: int, cursor: cursor) -> Optional[GetModelResponse]:
    select_query = "SELECT id, base_model_name, model_name, version FROM prod_storage.models WHERE id = %s AND deleted_flg = false;"
    cursor.execute(select_query, (id,))
    model_record = cursor.fetchone()
    if model_record is None:
        return None
    id, base_model_name, model_name, version = model_record
    return GetModelResponse(
        id=id, base_model_name=base_model_name, model_name=model_name, version=version
    )


async def create_inference(
    question_id: int, model_id: int, inference: LLModelResponse, cursor: cursor
) -> int:
    insert_query = """
        INSERT INTO prod_storage.questions_transformed
            (question_id, model_id, thinking, text, temperature)
        VALUES
            (%(question_id)s, %(model_id)s, %(reasoning)s, %(response)s, %(temperature)s)
        RETURNING id
        ;
    """
    data = inference.model_dump(include={"reasoning", "response", "temperature"})
    if "reasoning" not in data:
        data["reasoning"] = None
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
    return GetInferenceResponse(
        id=id, question_id=question_id, model_id=model_id, thinking=thinking, text=text
    )


async def get_question_inference_ids(question_id: int, cursor: cursor) -> List[int]:
    select_query = "SELECT id FROM prod_storage.questions_transformed WHERE question_id = %s AND deleted_flg = false;"
    cursor.execute(select_query, (question_id,))
    return [record[0] for record in cursor.fetchall()]


async def create_inference_score(
    inference_id: int, score: PostInferenceScoreRequest, cursor: cursor
) -> int:
    insert_query = """
        INSERT INTO prod_storage.inference_scores
            (inference_id, user_group_cd, helpful, does_not_reveal_answer, does_not_contain_errors, only_relevant_info)
        VALUES
            (%(inference_id)s, %(user_group_cd)s, %(helpful)s, %(does_not_reveal_answer)s, %(does_not_contain_errors)s, %(only_relevant_info)s)
        RETURNING id
        ;
    """
    data = score.model_dump(
        include={
            "user_group_cd",
            "helpful",
            "does_not_reveal_answer",
            "does_not_contain_errors",
            "only_relevant_info",
        }
    )
    data["inference_id"] = inference_id
    cursor.execute(insert_query, data)
    score_id = cursor.fetchone()[0]
    return score_id


async def get_inference_scores_all(
    user_group_cd: UserGroupCD, cursor: cursor
) -> List[GetInferenceScoreResponse]:
    select_query = """
        SELECT 
            isc.id,
            q.name as question_name, 
            qt.id as inference_id,
            isc.user_group_cd,
            isc.helpful,
            isc.does_not_reveal_answer,
            isc.does_not_contain_errors,
            isc.only_relevant_info
        FROM
            (SELECT * FROM prod_storage.inference_scores WHERE deleted_flg = false) isc
            INNER JOIN prod_storage.questions_transformed qt
                ON isc.inference_id = qt.id
            INNER JOIN prod_storage.questions q
                ON qt.question_id = q.id
            INNER JOIN prod_storage.link_user_group_x_level link
                ON q.level_cd = link.level_cd
                AND link.user_group_cd = %s
        ;
    """
    cursor.execute(select_query, (user_group_cd,))
    return [
        GetInferenceScoreResponse(
            id=id,
            question_name=question_name,
            inference_id=inference_id,
            user_group_cd=user_group_cd,
            helpful=helpful,
            does_not_reveal_answer=does_not_reveal_answer,
            does_not_contain_errors=does_not_contain_errors,
            only_relevant_info=only_relevant_info,
        )
        for id, question_name, inference_id, user_group_cd, helpful, does_not_reveal_answer, does_not_contain_errors, only_relevant_info in cursor.fetchall()
    ]


async def create_question_level(level: QuestionLevel, cursor: cursor) -> None:
    insert_query = """
        INSERT INTO prod_storage.dict_question_levels
            (level_cd, level_desc)
        VALUES
            (%(level_cd)s, %(level_desc)s)
        ON CONFLICT (level_cd) DO UPDATE 
        SET 
            level_desc = EXCLUDED.level_desc
        ;
    """
    cursor.execute(insert_query, level.model_dump(include={"level_cd", "level_desc"}))


async def create_user_group(group: PostUserGroupRequest, cursor: cursor) -> None:
    insert_query = """
        INSERT INTO prod_storage.dict_user_groups
            (user_group_cd, user_group_desc)
        VALUES
            (%(user_group_cd)s, %(user_group_desc)s)
        ON CONFLICT (user_group_cd) DO UPDATE 
        SET 
            user_group_desc = EXCLUDED.user_group_desc
        ;
    """
    cursor.execute(
        insert_query, group.model_dump(include={"user_group_cd", "user_group_desc"})
    )


async def create_user_group_x_level_link(
    group_level: PostUserGroupLevelAddRequest, cursor: cursor
) -> None:
    insert_query = """
        INSERT INTO prod_storage.link_user_group_x_level
            (user_group_cd, level_cd)
        VALUES
            (%(user_group_cd)s, %(level_cd)s)
        ;
    """
    cursor.execute(
        insert_query, group_level.model_dump(include={"user_group_cd", "level_cd"})
    )


async def set_user_group_x_level_link(
    group_levels: List[PostSetUserGroupLevelRequest], cursor: cursor
) -> None:
    delete_query = """
        DELETE FROM prod_storage.link_user_group_x_level
        WHERE user_group_cd = ANY(%s);
    """
    user_group_cds = [group.user_group_cd for group in group_levels]
    cursor.execute(delete_query, (user_group_cds,))

    insert_query = """
        INSERT INTO prod_storage.link_user_group_x_level
            (user_group_cd, level_cd)
        VALUES
            (%s, %s)
        ;
    """
    for group in group_levels:
        user_group_cd = group.user_group_cd
        for level_cd in group.level_cds:
            cursor.execute(insert_query, (user_group_cd, level_cd))


async def get_user_groups_all(cursor: cursor) -> List[UserGroup]:
    select_query = """
        SELECT  
            user_group_cd, user_group_desc
        FROM
            prod_storage.dict_user_groups
        WHERE
            deleted_flg = false
        ;
    """
    cursor.execute(select_query)
    return [
        UserGroup(user_group_cd=user_group_cd, user_group_desc=user_group_desc)
        for user_group_cd, user_group_desc in cursor.fetchall()
    ]


async def get_questions_all_admin(cursor: cursor) -> List[GetQuestionResponse]:
    """Get all not soft-deleted questions in database"""
    select_query = """
        SELECT 
            q.id, q.name, q.type, q.text 
        FROM 
            (SELECT * FROM prod_storage.questions WHERE deleted_flg = false) q
        ;
    """
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
        elif _type in QUESTION_CLOZE_TYPES:
            text = replace_and_append_options(text=text)

        inference_ids = await get_question_inference_ids(question_id=id, cursor=cursor)

        questions.append(
            GetQuestionResponse(
                id=id,
                name=name,
                type=_type,
                text=text,
                answers=answers,
                test_cases=test_cases,
                inference_ids=inference_ids,
            )
        )
    return questions


async def get_scores_for_inference(
    inference_id: int, cursor: cursor
) -> List[GetInferenceScoreResponse]:
    select_query = """
        SELECT 
            isc.id,
            q.name as question_name, 
            qt.id as inference_id,
            isc.user_group_cd,
            isc.helpful,
            isc.does_not_reveal_answer,
            isc.does_not_contain_errors,
            isc.only_relevant_info
        FROM
            (SELECT * FROM prod_storage.inference_scores WHERE inference_id = %s AND deleted_flg = false) isc
            INNER JOIN prod_storage.questions_transformed qt
                ON isc.inference_id = qt.id
            INNER JOIN prod_storage.questions q
                ON qt.question_id = q.id
        ;
    """
    cursor.execute(select_query, (inference_id,))
    return [
        GetInferenceScoreResponse(
            id=id,
            question_name=question_name,
            inference_id=inference_id,
            user_group_cd=user_group_cd,
            helpful=helpful,
            does_not_reveal_answer=does_not_reveal_answer,
            does_not_contain_errors=does_not_contain_errors,
            only_relevant_info=only_relevant_info,
        )
        for id, question_name, inference_id, user_group_cd, helpful, does_not_reveal_answer, does_not_contain_errors, only_relevant_info in cursor.fetchall()
    ]


async def get_questions(
    user_group_cd: UserGroupCD, cursor: cursor
) -> List[GetQuestionResponse]:
    """Get all not soft-deleted questions in database"""
    select_query = """
        SELECT 
            q.id, q.name, q.type, q.text 
        FROM 
            (SELECT * FROM prod_storage.questions WHERE deleted_flg = false) q
            INNER JOIN (SELECT * FROM prod_storage.link_user_group_x_level WHERE user_group_cd = %s) link
                ON q.level_cd = link.level_cd
            ;
    """
    cursor.execute(select_query, (user_group_cd,))

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
        elif _type in QUESTION_CLOZE_TYPES:
            text = replace_and_append_options(text=text)

        inference_ids = await get_question_inference_ids(question_id=id, cursor=cursor)

        questions.append(
            GetQuestionResponse(
                id=id,
                name=name,
                type=_type,
                text=text,
                answers=answers,
                test_cases=test_cases,
                inference_ids=inference_ids,
            )
        )
    return questions
