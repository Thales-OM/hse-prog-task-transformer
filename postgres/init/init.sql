-- init/init.sql
-- Create a schema if it does not exist
CREATE SCHEMA IF NOT EXISTS prod_storage;

-- Trigger for ensuring updated_at is set on every successful UPDATE
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create a table within the schema if it does not exist
CREATE TABLE
  IF NOT EXISTS prod_storage.dict_question_levels (
    level_cd VARCHAR(100) PRIMARY KEY,
    level_desc TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_flg BOOLEAN NOT NULL DEFAULT false
  );

CREATE TRIGGER set_dict_question_levels_updated_at
AFTER UPDATE ON prod_storage.dict_question_levels
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TABLE
  IF NOT EXISTS prod_storage.dict_user_groups (
    user_group_cd VARCHAR(100) PRIMARY KEY,
    user_group_desc TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_flg BOOLEAN NOT NULL DEFAULT false
  );

CREATE TRIGGER set_dict_user_groups_updated_at
AFTER UPDATE ON prod_storage.dict_user_groups
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


-- Append-only linking table
CREATE TABLE
  IF NOT EXISTS prod_storage.link_user_group_x_level (
    user_group_cd VARCHAR(100),
    level_cd VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
    PRIMARY KEY (user_group_cd, level_cd),
    FOREIGN KEY (user_group_cd) REFERENCES prod_storage.dict_user_groups (user_group_cd) ON DELETE CASCADE,
    FOREIGN KEY (level_cd) REFERENCES prod_storage.dict_question_levels (level_cd) ON DELETE CASCADE
  );


CREATE TABLE
  IF NOT EXISTS prod_storage.questions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(200) NOT NULL,
    text TEXT NOT NULL,
    level_cd VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_flg BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT questions_source_key_unique UNIQUE (name),
    FOREIGN KEY (level_cd) REFERENCES prod_storage.dict_question_levels (level_cd) ON DELETE SET NULL
  );

CREATE TRIGGER set_questions_updated_at
AFTER UPDATE ON prod_storage.questions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TABLE
  IF NOT EXISTS prod_storage.answers_multichoice (
    id SERIAL PRIMARY KEY,
    question_id INT NOT NULL,
    text TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    fraction REAL NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_flg BOOLEAN NOT NULL DEFAULT false,

    FOREIGN KEY (question_id) REFERENCES prod_storage.questions (id) ON DELETE CASCADE,

    CONSTRAINT answers_multichoice_source_key_unique UNIQUE (question_id, text)
  );

CREATE TRIGGER set_answers_multichoice_updated_at
AFTER UPDATE ON prod_storage.answers_multichoice
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TABLE
  IF NOT EXISTS prod_storage.answers_coderunner (
    id SERIAL PRIMARY KEY,
    question_id INT NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_flg BOOLEAN NOT NULL DEFAULT false,

    FOREIGN KEY (question_id) REFERENCES prod_storage.questions (id) ON DELETE CASCADE,

    CONSTRAINT answers_coderunner_source_key_unique UNIQUE (question_id, text)
  );

CREATE TRIGGER set_answers_coderunner_updated_at
AFTER UPDATE ON prod_storage.answers_coderunner
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TABLE
  IF NOT EXISTS prod_storage.test_cases (
    id SERIAL PRIMARY KEY,
    question_id INT NOT NULL,
    code TEXT,
    input TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    example BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_flg BOOLEAN NOT NULL DEFAULT false,

    FOREIGN KEY (question_id) REFERENCES prod_storage.questions (id) ON DELETE CASCADE,

    CONSTRAINT test_cases_source_key_unique UNIQUE (question_id, input)
  );

CREATE TRIGGER set_test_cases_updated_at
AFTER UPDATE ON prod_storage.test_cases
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TABLE
  IF NOT EXISTS prod_storage.models (
    id SERIAL PRIMARY KEY,
    base_model_name VARCHAR(200) NOT NULL,
    model_name VARCHAR(200) NOT NULL,
    version INT NOT NULL CHECK (version >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_flg BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT models_source_key_unique UNIQUE (base_model_name, version)
  );

CREATE TRIGGER set_models_updated_at
AFTER UPDATE ON prod_storage.models
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- Append-only table storing model inference
CREATE TABLE
  IF NOT EXISTS prod_storage.questions_transformed (
    id SERIAL PRIMARY KEY,
    question_id INT NOT NULL,
    model_id INT NOT NULL,
    thinking TEXT,
    text TEXT NOT NULL,
    temperature FLOAT CHECK(temperature > 0.0 and temperature <= 1.0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_flg BOOLEAN NOT NULL DEFAULT false,

    FOREIGN KEY (question_id) REFERENCES prod_storage.questions (id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES prod_storage.models (id) ON DELETE CASCADE
  );


-- Append-only table storing inference user scores
CREATE TABLE
  IF NOT EXISTS prod_storage.inference_scores (
    id SERIAL PRIMARY KEY,
    inference_id INT NOT NULL,
    user_group_cd VARCHAR(100),
    helpful INT NOT NULL CHECK (helpful BETWEEN 1 AND 5),
    does_not_reveal_answer INT NOT NULL CHECK (does_not_reveal_answer BETWEEN 1 AND 5),
    does_not_contain_errors INT NOT NULL CHECK (does_not_contain_errors in (1, 5)),
    only_relevant_info INT NOT NULL CHECK (only_relevant_info BETWEEN 1 AND 5),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_flg BOOLEAN NOT NULL DEFAULT false,

    FOREIGN KEY (inference_id) REFERENCES prod_storage.questions_transformed (id) ON DELETE CASCADE,
    FOREIGN KEY (user_group_cd) REFERENCES prod_storage.dict_user_groups (user_group_cd) ON DELETE SET NULL
  );
