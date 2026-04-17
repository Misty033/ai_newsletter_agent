import os
from dotenv import load_dotenv

load_dotenv()

# ─── Email ────────────────────────────────────────────────────────────────────
EMAIL_SENDER       = os.getenv("EMAIL_SENDER")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
FEEDBACK_BASE_URL  = os.getenv("FEEDBACK_BASE_URL", "http://localhost:5050")

# Add every friend's email here. They only give you their address — nothing else.
RECIPIENTS = [
    {"email": "202418007@dau.ac.in", "name": "Ashish",  "interests": ["research", "models"]},
    {"email": "202418064@dau.ac.in", "name": "Yashraj",  "interests": ["industry", "tools"]},
    {"email": "roy.misty.1204@gmail.com", "name": "Roy", "interests": ["research", "industry", "models", "tools"]},
]

# ─── Database ─────────────────────────────────────────────────────────────────
POSTGRES_CONFIG = {
    "host":     os.getenv("POSTGRES_HOST", "localhost"),
    "port":     int(os.getenv("POSTGRES_PORT", 5432)),
    "dbname":   os.getenv("POSTGRES_DB", "ai_news"),
    "user":     os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
}

# ─── Ollama ───────────────────────────────────────────────────────────────────
OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# ─── RSS Sources (with credibility weight) ────────────────────────────────────
# Weight multiplies the article's score. Higher = more trusted source.
RSS_FEEDS = [
    {"url": "https://openai.com/blog/rss.xml",                                           "name": "OpenAI",         "weight": 1.8},
    {"url": "https://www.deepmind.com/blog/rss.xml",                                     "name": "DeepMind",       "weight": 1.8},
    {"url": "https://venturebeat.com/category/ai/feed/",                                  "name": "VentureBeat",    "weight": 1.2},
    {"url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",        "name": "MIT Tech Review","weight": 1.4},
    {"url": "https://huggingface.co/blog/feed.xml",                                       "name": "HuggingFace",    "weight": 1.5},
    {"url": "https://ai.googleblog.com/feeds/posts/default",                              "name": "Google AI",      "weight": 1.6},
    {"url": "https://www.anthropic.com/rss.xml",                                          "name": "Anthropic",      "weight": 1.8},
    {"url": "https://bair.berkeley.edu/blog/feed.xml",                                    "name": "BAIR",           "weight": 1.3},
    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/",              "name": "TechCrunch AI",  "weight": 1.1},
    {"url": "https://the-decoder.com/feed/",                                              "name": "The Decoder",    "weight": 1.2},
]

# arXiv categories to pull from
ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "stat.ML", "cs.CL"]
ARXIV_MAX_RESULTS = 20  # per category per day

# Reddit subreddits to pull from (public JSON API — no key needed)
REDDIT_SUBS = ["MachineLearning", "artificial", "LocalLLaMA"]
REDDIT_MIN_UPVOTES = 100  # ignore low-engagement posts

# ─── Filtering ────────────────────────────────────────────────────────────────
AI_KEYWORDS = [
    "gpt", "llm", "large language model", "ai", "artificial intelligence",
    "machine learning", "deep learning", "neural network",
    "openai", "deepmind", "anthropic", "mistral", "llama", "gemini",
    "robotics", "reinforcement learning", "transformer", "diffusion",
    "agi", "foundation model", "fine-tun", "inference", "benchmark",
]

# ─── Ranking keywords ─────────────────────────────────────────────────────────
IMPORTANT_WORDS = [
    "release", "launch", "announce", "breakthrough", "new model",
    "research", "paper", "published", "funding", "billion", "acquired",
    "open source", "open-source", "beats", "outperforms", "record",
    "regulation", "ban", "law", "policy", "safety",
]

BIG_PLAYERS = [
    "openai", "deepmind", "google", "meta", "microsoft", "apple",
    "anthropic", "mistral", "stability", "hugging face", "nvidia",
    "amazon", "tesla", "xai", "inflection", "cohere",
]

# ─── Categories (used by categorizer.py) ──────────────────────────────────────
CATEGORIES = ["Model release", "Research paper", "Industry news", "Tools & repos", "Policy & regulation"]

# ─── Scoring thresholds ───────────────────────────────────────────────────────
MIN_SCORE_TO_SEND  = 3    # articles below this score are dropped even if nothing else qualifies
DAILY_TOP_N        = 5    # number of articles in daily digest
WEEKLY_TOP_N       = 10   # number of articles in Sunday deep-dive

# Velocity bonus: if same story appears in N+ sources, multiply score
VELOCITY_SOURCES_THRESHOLD = 3
VELOCITY_MULTIPLIER        = 1.5
