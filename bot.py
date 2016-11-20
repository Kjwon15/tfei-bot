import logging
import os

import telegram_bot

DB_URI = os.getenv('DATABASE_URL')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
THRESHOLD = os.getenv('THRESHOLD')

logging.basicConfig(
        format='%(asctime)s {%(module)s:%(levelname)s}: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(telegram_bot.__name__)
logger.setLevel(logging.INFO)

telegram_bot.start_bot(TELEGRAM_TOKEN, DB_URI, THRESHOLD,
          learning=True, answering=True)
