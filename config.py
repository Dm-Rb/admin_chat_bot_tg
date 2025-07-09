import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    phone_number = os.getenv("PHONE")
    total_wipe_confirms = int(os.getenv("TOTAL_WIPE_CONFIRMS"))
    personal_wipe_confirms = int(os.getenv("PERSONAL_WIPE_CONFIRMS"))
    folder_4_json = 'export_json_files'
    ai_token = os.getenv("AI_TOKEN")


config = Config()
