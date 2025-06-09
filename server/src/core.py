from typing import List
from bs4 import BeautifulSoup, Tag
from psycopg2.extensions import cursor
from src.config import settings
from src.constraints import (
    KNOWN_QUESTION_TYPES,
    QUESTION_CLOZE_TYPES,
    QUESTION_CODERUNNER_TYPES,
    QUESTION_MULTICHOICE_TYPES,
)
from src.logger import LoggerFactory
from src.utils import safe_deep_find
from src.database.crud import update_db_state
from src.exceptions import InvalidQuestionException
from src.schemas import AnswerMultichoice, AnswerCoderunner, TestCase, Question


logger = LoggerFactory.getLogger(__name__)


async def ingest_quiz_xml(xml_contents: str, cursor: cursor) -> List[int]:
    affected_question_ids = []
    questions = extract_quiz_data(xml_contents=xml_contents)
    for question in questions:
        question_id = await update_db_state(question=question, cursor=cursor)
        affected_question_ids.append(question_id)
    return affected_question_ids

def extract_quiz_data(xml_contents: str) -> List[Question]:
    """Extract questions and answers from XML content and return Question objects."""
    soup = BeautifulSoup(xml_contents, "lxml-xml")
    questions = []

    for question in soup.find_all("question"):
        _type = question.get("type", None)

        if _type is None:
            raise InvalidQuestionException("Question is missing type definition")

        if _type not in KNOWN_QUESTION_TYPES:
            raise InvalidQuestionException("Unkwnown Question type encountered")

        name_element = safe_deep_find(
            element=question, names=["name", "text"], default=None
        )
        name = name_element.text if name_element is not None else None

        # Extract and clean question text
        # [TODO] use safe_deep_find()
        qtext = question.find("questiontext").find("text").text

        answers = []
        test_cases = []

        if _type in QUESTION_MULTICHOICE_TYPES:
            answers = extract_mutlichoice_answers(content=question)
        elif _type in QUESTION_CODERUNNER_TYPES:
            answers = extract_coderunner_answers(content=question)
            test_cases = extract_coderunner_test_cases(content=question)

        questions.append(
            Question(
                name=name,
                type=_type,
                text=qtext,
                answers=answers,
                test_cases=test_cases,
            )
        )

    return questions


def extract_mutlichoice_answers(content: Tag) -> List[AnswerMultichoice]:
    raw_answers = []
    fractions = []

    for answer in content.find_all("answer"):
        # [TODO] use safe_deep_find()
        text = element.text if (element := answer.find("text")) else ""
        fraction = float(answer.get("fraction", "0"))
        raw_answers.append((text, fraction))
        fractions.append(fraction)

    if not raw_answers:  # Questions without answer options
        return []

    max_fraction = max(fractions) if fractions else 0

    # Build Answer objects
    answers = []
    for text, fraction in raw_answers:
        is_correct = fraction == max_fraction and max_fraction > 0

        answers.append(
            AnswerMultichoice(text=text, is_correct=is_correct, fraction=fraction)
        )
    return answers


def extract_coderunner_answers(content: Tag) -> List[AnswerCoderunner]:
    answers = []

    for answer in content.find_all("answer"):
        text = answer.text
        answers.append(AnswerCoderunner(text=text))

    return answers


def extract_coderunner_test_cases(content: Tag) -> List[TestCase]:
    testcases = content.find("testcases")
    if testcases is None:
        return []

    test_cases_output = []
    for testcase in content.find_all("testcase"):
        testcode_element = safe_deep_find(element=testcase, names=["testcode", "text"])
        testcode = testcode_element.text if testcode_element is not None else None

        stdin_element = safe_deep_find(element=testcase, names=["stdin", "text"])
        stdin = stdin_element.text if stdin_element is not None else None

        expected_element = safe_deep_find(element=testcase, names=["expected", "text"])
        expected = expected_element.text if expected_element is not None else None

        useasexample = testcase.get("useasexample", "0") == "1"

        test_cases_output.append(
            TestCase(
                code=testcode,
                input=stdin,
                expected_output=expected,
                example=useasexample,
            )
        )
    return test_cases_output
