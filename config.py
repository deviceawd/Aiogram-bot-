import logging
import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Чтобы логи выводились в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

#Конфигурация бота
TOKEN = os.getenv('TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# URL для получения курсов валют
CSV_URL = os.getenv('CSV_URL')

LOGO_PATH = os.getenv('LOGO_PATH')
# URL для получения адресов кошельков
WALLET_SHEET_URL = os.getenv('WALLET_SHEET_URL')

# API ключи для проверки транзакций
TRONSCAN_API_KEY = os.getenv('TRONSCAN_API_KEY')
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY')
# TRONSCAN не требует API ключа для базовых запросов

TRC20_CONFIRMATIONS = int(os.getenv('TRC20_CONFIRMATIONS'))
TRONSCAN_API = os.getenv('TRONSCAN_API')
ERC20_CONFIRMATIONS = int(os.getenv('ERC20_CONFIRMATIONS'))


REDIS_URL = os.getenv('REDIS_URL')
REDIS_DB_FSM = os.getenv('REDIS_DB_FSM')
REDIS_DB = os.getenv('REDIS_DB')
REDIS_BACKEND_DB = os.getenv('REDIS_BACKEND_DB')
REDIS_KEY_PREFIX_ERC = os.getenv('REDIS_KEY_PREFIX_ERC')
REDIS_KEY_PREFIX_TRC = os.getenv('REDIS_KEY_PREFIX_TRC')



# ID чата администратора для заявок
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')  # Замените на реальный ID админ-группы

# Telethon (userbot)
TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')            # укажи свой api_id с my.telegram.org
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')         # укажи свой api_hash с my.telegram.org
TELETHON_SESSION = os.getenv('TELETHON_SESSION')  # имя файла сессии (создастся после логина)

GOOGLE_CREDENTIALS  = {
    "type": os.getenv("GOOGLE_TYPE"),
    "project_id": os.getenv("GOOGLE_PROJECT_ID"),
    "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n"),
    "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
    "auth_uri": os.getenv("GOOGLE_AUTH_URI"),
    "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("GOOGLE_AUTH_PROVIDER_X509_CRT_URL"),
    "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL"),
    "universe_domain": os.getenv("GOOGLE_UNIVERSE_DOMAIN")
}