from pydantic import BaseModel, model_validator, Field, ConfigDict, field_validator, ValidationError
from typing import Optional, List, Union, get_args, Any
import re
from openai.types.chat import ChatCompletion
from src.exceptions import  UnrecognizedQuestionTypeException, AnswerMismatchException, InvalidQuestionException
from src.constraints import KNOWN_QUESTION_TYPES, QUESTION_MULTICHOICE_TYPES, QUESTION_CODERUNNER_TYPES, QUESTION_CLOZE_TYPES
from src.utils import render_md_to_html, clean_html_tags, convert_code_blocks_to_html
from src.models.constraints import DEFAULT_MODEL_TEMPERATURE
from src.types import UserGroupCD, LevelCD, PEM, InferenceScoreVal, ModelTemperature, Language


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


class GetQuestionResponse(Question):
    id: int
    inference_ids: List[int] = Field(default_factory=list)

class QuestionPageResponse(GetQuestionResponse):
    id: int
    text_rendered: str
    text_clean: str
    answers: List[AnswerPageResponse] = Field(default_factory=list)
    test_cases: List[TestCase] = Field(default_factory=list)

    @classmethod
    def from_question_response(cls, question_response: GetQuestionResponse) -> "QuestionPageResponse":
        return cls(
            id=question_response.id,
            name=question_response.name,
            type=question_response.type,
            text=question_response.text,
            answers=[answer.render() for answer in question_response.answers],
            test_cases=question_response.test_cases,
            text_rendered=convert_code_blocks_to_html(text=question_response.text), 
            text_clean=clean_html_tags(question_response.text),
            inference_ids=question_response.inference_ids
        )


class QuestionInferencePageResponse(GetQuestionResponse):
    id: int
    text_rendered: str
    text_clean: str
    answers: List[AnswerPageResponse] = Field(default_factory=list)
    test_cases: List[TestCase] = Field(default_factory=list)
    inference_id: int
    inference_text: str

    @classmethod
    def from_question_response(cls, question_response: GetQuestionResponse, inference: "GetInferenceResponse") -> "QuestionInferencePageResponse":
        return cls(
            id=question_response.id,
            name=question_response.name,
            type=question_response.type,
            text=question_response.text,
            answers=[answer.render() for answer in question_response.answers],
            test_cases=question_response.test_cases,
            text_rendered=convert_code_blocks_to_html(text=question_response.text), 
            text_clean=clean_html_tags(question_response.text),
            inference_ids=question_response.inference_ids,
            inference_id=inference.id,
            inference_text=inference.text
        )


class QuestionsRandomIdResponse(BaseModel):
    id: int


class LLModelResponse(BaseModel):
    response: str

    @classmethod
    def from_completion(cls, completion: ChatCompletion) -> "LLModelResponse":
        choice = completion.choices[0]
        response_content = choice.message.content
        return response_content


class ReasoningLLModelResponse(LLModelResponse):
    reasoning: str
    
    @classmethod
    def from_completion(cls, completion: ChatCompletion) -> "ReasoningLLModelResponse":
        choice = completion.choices[0]
        response_content = choice.message.content

        # Extract the reasoning content between <think> tags
        reasoning_match = re.search(r'<think>(.*?)</think>', response_content, re.DOTALL)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else None

        # Remove the <think> block to get the final response
        response = re.sub(r'<think>.*?</think>', '', response_content, flags=re.DOTALL).strip()

        return cls(response=response, reasoning=reasoning)


class GetInferenceResponse(BaseModel):
    id: int
    question_id: int
    model_id: int
    thinking: Optional[str] = None
    text: str


class PostModelRequest(BaseModel):
    base_model_name: str
    model_name: str


class GetModelResponse(BaseModel):
    id: int
    base_model_name: str
    model_name: str
    version: int


class PostInferenceRequest(BaseModel):
    question_id: int
    model_id: int
    temperature: ModelTemperature = DEFAULT_MODEL_TEMPERATURE


class InferenceScore(BaseModel):
    helpful: InferenceScoreVal
    does_not_reveal_answer: InferenceScoreVal
    does_not_contain_errors: InferenceScoreVal
    only_relevant_info: InferenceScoreVal

class PostInferenceScoreRequest(InferenceScore):
    user_group_cd: UserGroupCD


class GetInferenceScoreResponse(InferenceScore):
    id: int
    question_name: str
    inference_id: int


class RSAKeyPair(BaseModel):
    public_pem: PEM
    private_pem: PEM


class PostRenewTokenResponse(BaseModel):
    private_pem: PEM


class QuestionLevel(BaseModel):
    level_cd: LevelCD
    level_desc: Optional[str] = None


class UserGroup(BaseModel):
    user_group_cd: UserGroupCD
    user_group_desc: Optional[str] = None


class PostUserGroupRequest(UserGroup):
    pass


class GetUserGroupResponse(UserGroup):
    pass


class PostUserGroupLevelAddRequest(BaseModel):
    user_group_cd: UserGroupCD
    level_cd: LevelCD


class PostSetUserGroupLevelRequest(BaseModel):
    user_group_cd: UserGroupCD
    level_cds: List[LevelCD]


class LanguagePageResponse(BaseModel):
    available: List[Language] = [lang for lang in get_args(Language)]
    current: Language
    pack: Any
    