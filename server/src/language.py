from pydantic import BaseModel, model_validator, ValidationError
from typing import Dict, get_args, Optional
from src.types import BaseName, BaseDesc, Language
from src.config import settings


class LanguageManager(BaseModel):
    language_packs: Dict[Language, "LanguagePack"]
    default_language: Language

    def get_language_pack(self, language: Optional[Language] = None) -> "LanguagePack":
        if language is None:
            language = self.default_language
        if language not in self.language_packs:
            raise ValueError(f'Language "{language}" is missing from language packs')
        return self.language_packs[language]

    @model_validator(mode="after")
    def validate_languages(self):
        for language in get_args(Language):
            if language not in self.language_packs:
                raise ValidationError(f"A language pack is missing for a declared language: {language}")
        return self

class LanguagePack(BaseModel):
    main: "Main"
    dashboard: "Dashboard"
    question_list: "QuestionList"
    question: "Question"
    inference: "Inference"
    score_list: "ScoreList"
    tutorial: "Tutorial"

class Main(BaseModel):
    header: BaseName

class Dashboard(BaseModel):
    header: BaseName
    question_list_nm: BaseName
    question_list_desc: BaseDesc
    random_question_nm: BaseName
    random_question_desc: BaseDesc
    inference_scores_nm: BaseName
    inference_scores_desc: BaseDesc
    tutorial_nm: BaseName
    tutorial_desc: BaseDesc

class QuestionList(BaseModel):
    header: BaseName
    back_button_1: BaseName
    detail_link: BaseName

class Question(BaseModel):
    back_button_1: BaseName
    question_text_header: BaseName
    answers_header: BaseName
    test_cases_header: BaseName
    inferences_header: BaseName
    inference_item_nm: BaseName

class Inference(BaseModel):
    back_button_1: BaseName
    back_button_2: BaseName
    question_text_header: BaseName
    answers_header: BaseName
    test_cases_header: BaseName
    inference_header: BaseName
    rating_header: BaseName
    rating_helpful_nm: BaseName
    rating_no_answer_nm: BaseName
    rating_no_error_nm: BaseName
    rating_relevant_nm: BaseName

class ScoreList(BaseModel):
    header: BaseName
    back_button_1: BaseName
    rating_helpful_nm: BaseName
    rating_no_answer_nm: BaseName
    rating_no_error_nm: BaseName
    rating_relevant_nm: BaseName

class Tutorial(BaseModel):
    back_button_1: BaseName
    question_text_header: BaseName
    answers_header: BaseName
    inference_header: BaseName
    rating_helpful_nm: BaseName
    rating_no_answer_nm: BaseName
    rating_no_error_nm: BaseName
    rating_relevant_nm: BaseName

ru_language_pack = LanguagePack(
    main=Main(
        header="Выберите свое направление подготовки",
    ),
    dashboard=Dashboard(
        header="Как ИИ делает программирование понятнее? Ваше мнение важно!",
        question_list_nm="Список Заданий",
        question_list_desc="Все доступные задания и их ИИ варианты",
        random_question_nm="Случайное Задание",
        random_question_desc="Получите случайное задание из списка",
        inference_scores_nm="История Оценок",
        inference_scores_desc="Посмотрите как другие респонденты оценили ответы ИИ",
        tutorial_nm="Инструкции",
        tutorial_desc="Ознакомьтесь с критериями оценки и примерами",
    ),
    question_list=QuestionList(
        header="Задания",
        back_button_1="Дэшборд",
        detail_link="Подробнее",
    ),
    question=Question(
        back_button_1="Список Заданий",
        question_text_header="Текст задания",
        answers_header="Ответы",
        test_cases_header="Тестовые данные",
        inferences_header="ИИ помощник",
        inference_item_nm="Вариант",
    ),
    inference=Inference(
        back_button_1="Список Заданий",
        back_button_2="Задание",
        question_text_header="Текст задания",
        answers_header="Ответы",
        test_cases_header="Тестовые данные",
        inference_header="ИИ помощник",
        rating_header="Оцените ответ",
        rating_helpful_nm="Полезно",
        rating_no_answer_nm="Не раскрывает ответ",
        rating_no_error_nm="Не содержит ошибок",
        rating_relevant_nm="Релевантно",
    ),
    score_list=ScoreList(
        header="История оценок",
        back_button_1="Дэшборд",
        rating_helpful_nm="Полезно",
        rating_no_answer_nm="Не раскрывает ответ",
        rating_no_error_nm="Не содержит ошибок",
        rating_relevant_nm="Релевантно",
    ),
    tutorial=Tutorial(
        back_button_1="Дэшборд",
        question_text_header="Текст задания",
        answers_header="Ответы",
        inference_header="Примеры оценки ИИ помощника",
        rating_helpful_nm="Полезно",
        rating_no_answer_nm="Не раскрывает ответ",
        rating_no_error_nm="Не содержит ошибок",
        rating_relevant_nm="Релевантно",
    )
)

en_language_pack = LanguagePack(
    main=Main(
        header="Choose Your Study Program"
    ),
    dashboard=Dashboard(
        header="How Does AI Make Programming Clearer? Your Opinion Matters!",
        question_list_nm="Questions List",
        question_list_desc="List all available questions",
        random_question_nm="Random Question",
        random_question_desc="Pick a random question from the list",
        inference_scores_nm="User Scores",
        inference_scores_desc="See how other users scored AI suggestions",
        tutorial_nm="Scoring Tutorial",
        tutorial_desc="See how the scoring system is intended to be used (with examples)"
    ),
    question_list=QuestionList(
        header="Questions List",
        back_button_1="Back to Dashboard",
        detail_link="View Details",
    ),
    question=Question(
        back_button_1="Back to Questions List",
        question_text_header="Question Text",
        answers_header="Answers",
        test_cases_header="Test Cases",
        inferences_header="AI Inferences",
        inference_item_nm="Inference",
    ),
    inference=Inference(
        back_button_1="Back to Questions List",
        back_button_2="Back to Question",
        question_text_header="Question Text",
        answers_header="Answers",
        test_cases_header="Test Cases",
        inference_header="AI Inference",
        rating_header="Rate this Analysis",
        rating_helpful_nm="Helpful",
        rating_no_answer_nm="Does not reveal answer",
        rating_no_error_nm="Does not contain errors",
        rating_relevant_nm="Relevance",
    ),
    score_list=ScoreList(
        header="User Scores",
        back_button_1="Back to Dashboard",
        rating_helpful_nm="Helpful",
        rating_no_answer_nm="Does not reveal answer",
        rating_no_error_nm="Does not contain errors",
        rating_relevant_nm="Relevance",
    ),
    tutorial=Tutorial(
        back_button_1="Back to Dashboard",
        question_text_header="Question Text",
        answers_header="Answers",
        inference_header="AI Inference Scoring Example",
        rating_helpful_nm="Helpful",
        rating_no_answer_nm="Does not reveal answer",
        rating_no_error_nm="Does not contain errors",
        rating_relevant_nm="Relevance",
    )
)


language_manager = LanguageManager(
    language_packs={
        "ru": ru_language_pack,
        "en": en_language_pack,
    },
    default_language=settings.frontend.default_language,
)
