-- init/init.sql
-- Create a schema if it does not exist
CREATE SCHEMA IF NOT EXISTS prod_storage;

-- Create a table within the schema if it does not exist
CREATE TABLE
  IF NOT EXISTS prod_storage.questions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(200) NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_flg BOOLEAN NOT NULL DEFAULT false
  );

CREATE TABLE
  IF NOT EXISTS prod_storage.answers_multichoice (
    id SERIAL PRIMARY KEY,
    question_id INT,
    text TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    fraction REAL NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_flg BOOLEAN NOT NULL DEFAULT false,

    FOREIGN KEY (question_id) REFERENCES prod_storage.questions (id) ON DELETE SET NULL
  );


CREATE TABLE
  IF NOT EXISTS prod_storage.answers_coderunner (
    id SERIAL PRIMARY KEY,
    question_id INT,
    text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_flg BOOLEAN NOT NULL DEFAULT false,

    FOREIGN KEY (question_id) REFERENCES prod_storage.questions (id) ON DELETE SET NULL
  );


CREATE TABLE
  IF NOT EXISTS prod_storage.test_cases (
    id SERIAL PRIMARY KEY,
    question_id INT,
    code TEXT,
    input TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    example BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_flg BOOLEAN NOT NULL DEFAULT false,

    FOREIGN KEY (question_id) REFERENCES prod_storage.questions (id) ON DELETE SET NULL
  );
