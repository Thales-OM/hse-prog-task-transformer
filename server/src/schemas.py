from pydantic import BaseModel, model_validator, Field, ConfigDict, field_validator, ValidationError
from typing import Optional, List, Union
from src.exceptions import  UnrecognizedQuestionTypeException, AnswerMismatchException, InvalidQuestionException
from src.constraints import KNOWN_QUESTION_TYPES, QUESTION_MULTICHOICE_TYPES, QUESTION_CODERUNNER_TYPES, QUESTION_CLOZE_TYPES
from src.utils import render_md_to_html, clean_html_tags, convert_code_blocks_to_html


class MessageSuccessResponse(BaseModel):
    message: str


class Answer(BaseModel):
    text: str
    model_config = ConfigDict(extra="ignore")

    def render(self) -> "AnswerPageResponse":
        return AnswerPageResponse.from_answer(answer=self)


class AnswerMultichoice(Answer):
    is_correct: bool = False
    fraction: Optional[float] = None

    def render(self) -> "AnswerMultichoicePageResponse":
        return AnswerMultichoicePageResponse.from_answer(answer=self)


class AnswerCoderunner(Answer):
    def render(self) -> "AnswerCoderunnerPageResponse":
        return AnswerCoderunnerPageResponse.from_answer(answer=self)


class AnswerPageResponse(Answer):
    text_rendered: str
    text_clean: str

    @classmethod
    def from_answer(cls, answer: Answer) -> "AnswerPageResponse":
        answer_dict = answer.model_dump()
        return cls(**answer_dict, text_rendered=convert_code_blocks_to_html(text=answer.text), text_clean=clean_html_tags(answer.text))


class AnswerMultichoicePageResponse(AnswerMultichoice, AnswerPageResponse):
    pass

class AnswerCoderunnerPageResponse(AnswerCoderunner, AnswerPageResponse):
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
    answers: List[Union[AnswerMultichoice, AnswerCoderunner, Answer]] = Field(default_factory=list)
    test_cases: List[TestCase] = Field(default_factory=list)

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
                try:
                    self.answers = [AnswerMultichoice(**answer.model_dump()) for answer in self.answers]
                except ValidationError as er:
                    raise AnswerMismatchException(f"Received incompatible Answers of unexpected type {expected_answer_type} for Multichoice type question:\n{er}")
            if self.type in QUESTION_CODERUNNER_TYPES and expected_answer_type is not AnswerCoderunner:
                try:
                    self.answers = [AnswerCoderunner(**answer.model_dump()) for answer in self.answers]
                except ValidationError as er:
                    raise AnswerMismatchException(f"Received incompatible Answers of unexpected type {expected_answer_type} for Coderunner type question:\n{er}")
            if self.type in QUESTION_CLOZE_TYPES:
                raise AnswerMismatchException(f"Received unexpected Answers for Cloze type question")
        return self

    @model_validator(mode="after")
    def validate_test_cases(self):
        if self.test_cases and self.type not in QUESTION_CODERUNNER_TYPES:
            raise InvalidQuestionException("Question received test cases despite not being Coderunner type")
        return self


class QuestionPageResponse(Question):
    id: int
    text_rendered: str
    text_clean: str
    answers: List[AnswerPageResponse] = Field(default_factory=list)
    test_cases: List[TestCase] = Field(default_factory=list)

    @classmethod
    def from_question(cls, id: int, question: Question) -> "QuestionPageResponse":
        return cls(
            id=id,
            name=question.name,
            type=question.type,
            text=question.text,
            answers=[answer.render() for answer in question.answers],
            test_cases=question.test_cases,
            text_rendered=convert_code_blocks_to_html(text=question.text), 
            text_clean=clean_html_tags(question.text)
        )


class QuestionsRandomIdResponse(BaseModel):
    id: int
