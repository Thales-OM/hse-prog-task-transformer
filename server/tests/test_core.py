# tests/test_core.py
import pytest
from src.core import extract_quiz_data
from src.exceptions import InvalidQuestionException
from src.schemas import AnswerMultichoice

SAMPLE_XML = """<?xml version="1.0" ?>
<quiz>
  <question type="multichoice">
    <name><text>Sample Question</text></name>
    <questiontext><text>What is 2+2?</text></questiontext>
    <answer fraction="100">
      <text>4</text>
    </answer>
    <answer fraction="0">
      <text>5</text>
    </answer>
  </question>
</quiz>"""

def test_extract_quiz_data():
    questions = extract_quiz_data(SAMPLE_XML)
    assert len(questions) == 1
    question = questions[0]
    assert question.name == "Sample Question"
    assert question.type == "multichoice"
    assert len(question.answers) == 2
    assert isinstance(question.answers[0], AnswerMultichoice)

def test_invalid_question_type():
    invalid_xml = SAMPLE_XML.replace("multichoice", "invalidtype")
    with pytest.raises(InvalidQuestionException):
        extract_quiz_data(invalid_xml)
