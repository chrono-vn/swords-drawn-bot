import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SHEET_ID = os.getenv('SHEET_ID')
CREDS_FILE = "credentials.json"
DB_FILE = "cooldowns.db"
MAX_CHARGES = 3

OFFICER_ROLE_IDS = [788909020052193344]
CORE_MEMBER_ROLE_IDS = [832772694898245633]