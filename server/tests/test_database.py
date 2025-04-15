# tests/test_database.py
import pytest
from src.database.pool import ConnectionPoolManager
from src.database.crud import *
from src.schemas import Question, AnswerMultichoice, AnswerCoderunner, TestCase, PostModelRequest
from psycopg2 import IntegrityError

def test_connection_pool(mock_db_pool):
    assert ConnectionPoolManager._pool is not None
    assert ConnectionPoolManager._pool.minconn >= 1
    assert ConnectionPoolManager._pool.maxconn >= ConnectionPoolManager._pool.minconn

@pytest.mark.asyncio
async def test_question_crud(db_cursor):
    # Test question creation
    test_question = Question(
        name="Test Question",
        type="multichoice",
        text="What is 2+2?",
        answers=[AnswerMultichoice(text="4", is_correct=True, fraction=1.0)]
    )
    
    question_id = await create_question(test_question, db_cursor)
    assert isinstance(question_id, int)
    
    # Test question retrieval
    question = await get_question(question_id, db_cursor)
    assert question.name == "Test Question"
    assert question.type == "multichoice"
    
    # Test answer retrieval
    answers = await get_answers_multichoice(question_id, db_cursor)
    assert len(answers) == 1
    assert answers[0].text == "4"
    
    # Test update with same name (should upsert)
    new_question = test_question.model_copy()
    new_question.text = "Updated question text"
    updated_id = await create_question(new_question, db_cursor)
    assert updated_id == question_id
    
    updated_question = await get_question(question_id, db_cursor)
    assert updated_question.text == "Updated question text"

@pytest.mark.asyncio
async def test_model_crud(db_cursor):
    test_model = PostModelRequest(
        base_model_name="gpt-3.5",
        model_name="math-specialist"
    )
    
    model_id = await create_model(test_model, db_cursor)
    assert isinstance(model_id, int)
    
    models = await get_models_all(db_cursor)
    assert len(models) == 1
    assert models[0].model_name == "math-specialist"
    
    # Test version increment
    same_base_model = test_model.model_copy()
    same_base_model.model_name = "updated-name"
    new_model_id = await create_model(same_base_model, db_cursor)
    
    models = await get_models_all(db_cursor)
    assert len(models) == 2
    assert models[1].version == models[0].version + 1

@pytest.mark.asyncio
async def test_unique_constraints(db_cursor):
    question = Question(
        name="Unique Question",
        type="multichoice",
        text="Test text"
    )
    
    # First insert should succeed
    await create_question(question, db_cursor)
    
    # Second insert should violate unique constraint
    with pytest.raises(IntegrityError):
        await create_question(question, db_cursor)
