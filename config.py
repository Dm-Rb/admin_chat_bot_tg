import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    phone_number = os.getenv("PHONE")
    ai_token = os.getenv("AI_TOKEN")
    ai_temperature = float(os.getenv("AI_TEMPERATURE"))


config = Config()
