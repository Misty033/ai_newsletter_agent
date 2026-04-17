#!/bin/bash
# Creates the application database 'ai_news' inside the Docker postgres container.
# Runs automatically on first container start (placed in /docker-entrypoint-initdb.d/).
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE ai_news;
    GRANT ALL PRIVILEGES ON DATABASE ai_news TO $POSTGRES_USER;
EOSQL

echo "[init-db] 'ai_news' database created and granted to $POSTGRES_USER."
