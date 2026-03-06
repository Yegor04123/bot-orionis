import os
from dotenv import load_dotenv

load_dotenv()

# Discord Bot
BOT_TOKEN = os.getenv('BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))
APPLICATION_CHANNEL_ID = int(os.getenv('APPLICATION_CHANNEL_ID'))
REVIEW_CHANNEL_ID = int(os.getenv('REVIEW_CHANNEL_ID'))
LOGS_CHANNEL_ID = int(os.getenv('LOGS_CHANNEL_ID'))
PLAYER_ROLE_ID = int(os.getenv('PLAYER_ROLE_ID'))
ADMIN_ROLES = [int(role_id) for role_id in os.getenv('ADMIN_ROLES').split(',')]

# Minecraft RCON
RCON_HOST = os.getenv('RCON_HOST')
RCON_PORT = int(os.getenv('RCON_PORT'))
RCON_PASSWORD = os.getenv('RCON_PASSWORD')

# Database
DB_PATH = os.getenv('DB_PATH', 'applications.db')

# Application Settings
APPLICATION_COOLDOWN_DAYS = 14
MIN_AGE = 14