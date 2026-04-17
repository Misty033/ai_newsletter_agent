# Local Setup & Deployment Guide ⚙️

Follow these exact steps to run the AI Newsletter Agent on your local Windows/Mac machine.

## Prerequisites
1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. Install [Ollama](https://ollama.com/) locally.
3. Install Python 3.10+.
4. Have a Google Account with "App Passwords" enabled.

---

## 1. Environment Secrets Configuration
1. Rename `.env.example` to `.env`.
2. Fill out your App Password and database secrets:
```env
EMAIL_SENDER=your-email@gmail.com
EMAIL_APP_PASSWORD=your_16_digit_app_password
FEEDBACK_BASE_URL=http://localhost:5050
OLLAMA_URL=http://localhost:11434/api/generate
```
*(Similarly, update the variables inside `/airflow-docker/.env` to mirror these!)*

## 2. Booting the AI Engine (Llama 3)
The system requires an LLM to evaluate text. Keep this running in the background.
```cmd
ollama pull llama3
ollama serve
```

## 3. Launching Postgres & Apache Airflow
Because Airflow does not natively support Windows, you must run it via Docker Compose. This will spin up the webserver, scheduler, triggerer, Redis cache, and our PostgreSQL database.
Ensure you are inside the `airflow-docker` directory:
```bash
cd airflow-docker
docker compose up -d
```
> **Note:** The first time you run this, Airflow spends ~5-10 minutes installing dependencies into the container.
> Airflow UI will become available at: **http://localhost:8081** (Login: `admin` / `admin`)

## 4. Launching the Web Tools (Host Machine)
Open a new terminal window in the root directory.

**A. Start the Feedback Loop Server:**
This listens for 👍/👎 clicks from the emails.
```bash
python feedback_server.py
```
*(Runs on **http://localhost:5050**)*

**B. Start the Archive Dashboard:**
A beautiful UI to search historical AI news.
```bash
streamlit run dashboard.py
```
*(Runs on **http://localhost:8501**)*

## 5. Automating the Pipeline
1. Navigate to your Airflow UI: **http://localhost:8081**.
2. To turn the system ON, simply click the toggle switch next to `ai_news_daily` to **Unpause**.
3. It will automatically wake up and trigger execution at 8:00 AM every day!
*(To manual test right now, click the `▶ Play` button and hit "Trigger DAG").*
