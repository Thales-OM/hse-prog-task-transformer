from pydantic import BaseModel, model_validator, Field, ConfigDict, field_validator
from typing import Optional, List
from src.exceptions import  UnrecognizedQuestionTypeException, AnswerMismatchException, InvalidQuestionException
from src.constraints import KNOWN_QUESTION_TYPES, QUESTION_MULTICHOICE_TYPES, QUESTION_CODERUNNER_TYPES, QUESTION_CLOZE_TYPES


class MessageSuccessResponse(BaseModel):
    message: str


class Answer(BaseModel):
    text: str
    model_config = ConfigDict(extra="ignore")


class AnswerMultichoice(Answer):
    is_correct: bool = False
    fraction: Optional[float] = None


class AnswerCoderunner(Answer):
    pass


class TestCase(BaseModel):
    code: Optional[str] = None
    input: str
    expected_output: str
    example: Optional[bool] = None


class Question(BaseModel):
    name: str
    type: str
    text: str
    answers: List[Answer] = Field(default_factory=list, min_items=1)
    test_cases: List[TestCase] = Field(default_factory=list, min_items=1)

    @field_validator("type", mode="after")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in KNOWN_QUESTION_TYPES:
            raise UnrecognizedQuestionTypeException(f"Unrecognized question type encountered: {value}")
        return value
    
    @model_validator(mode="after")
    def validate_answer_types(self):
        answer_types = [type(answer) for answer in self.answers]
        expected_answer_type = None
        
        if len(answer_types) > 0:
            first_answer_type = answer_types[0]
            if any([answer_type is not first_answer_type for answer_type in answer_types]):
                raise AnswerMismatchException("Different answer types received in question")
            expected_answer_type = first_answer_type
        
            if self.type in QUESTION_MULTICHOICE_TYPES and expected_answer_type is not AnswerMultichoice:
                raise AnswerMismatchException(f"Received Answers of unexpected type {expected_answer_type} for Multichoice type question")
            if self.type in QUESTION_CODERUNNER_TYPES and expected_answer_type is not AnswerCoderunner:
                raise AnswerMismatchException(f"Received Answers of unexpected type {expected_answer_type} for Coderunner type question")
            if self.type in QUESTION_CLOZE_TYPES:
                raise AnswerMismatchException(f"Received unexpected Answers for Cloze type question")
        return self

    @model_validator(mode="after")
    def validate_test_cases(self):
        if self.test_cases and self.type not in QUESTION_CODERUNNER_TYPES:
            raise InvalidQuestionException("Question received test cases despite not being Coderunner type")
        return self


