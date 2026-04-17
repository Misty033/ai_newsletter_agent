-- Runs once on first postgres container start.
-- Creates the application database alongside the airflow metadata database.

CREATE DATABASE ai_news;
GRANT ALL PRIVILEGES ON DATABASE ai_news TO airflow;
