import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TC_BOT_TOKEN", "")
BOT_SECRET = os.getenv("BOT_SECRET", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://talentcheck-tau.vercel.app")
