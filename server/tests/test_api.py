# tests/test_api.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.schemas import GetInferenceResponse, MessageSuccessResponse


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

def test_health_check(test_client):
    response = test_client.get("/health/ping")
    assert response.status_code == 200
    assert response.json() == {"message": "pong"}

def test_get_questions_all(test_client, db_cursor):
    response = test_client.get("/questions/all")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_upload_quiz_xml(test_client):
    response = test_client.post(
        "/quiz/xml",
        content=SAMPLE_XML,
        headers={"Content-Type": "application/xml"}
    )
    assert response.status_code == 201
    assert MessageSuccessResponse(**response.json())

def test_get_random_question_id(test_client):
    response = test_client.get("/questions/random/id")
    assert response.status_code == 200
    assert "id" in response.json()

def test_inference_workflow(test_client, mock_openai_client):
    # Create model
    model_data = {"base_model_name": "test", "model_name": "test-model"}
    test_client.post("/models/new", json=model_data)
    
    # Create question
    test_client.post("/quiz/xml", content=SAMPLE_XML, headers={"Content-Type": "application/xml"})
    
    # Create inference
    inference_data = {
        "question_id": 1,
        "model_id": 1,
        "temperature": 0.5
    }
    response = test_client.post("/inference/new", json=inference_data)
    assert response.status_code == 201
    
    # Get inference
    response = test_client.get("/inference/1")
    assert response.status_code == 200
    assert GetInferenceResponse(**response.json())

@pytest.fixture
def mock_openai_client(monkeypatch):
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content="Test response<think>Test reasoning</think>"))]
    ))
    monkeypatch.setattr("src.api.routes.upload.openai.AsyncClient", MagicMock(return_value=mock_client))
    return mock_client