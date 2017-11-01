import logging
import os

import telegram_bot
from autotweet import logger_factory

DB_URI = os.getenv('DATABASE_URL')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
THRESHOLD = os.getenv('THRESHOLD')

logging.basicConfig(
        format='%(asctime)s {%(module)s:%(levelname)s}: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(telegram_bot.__name__)
logger.setLevel(logging.DEBUG)
logger_factory.set_level(logging.DEBUG)

logger.info('Starting telegram bot...')
telegram_bot.start_bot(
    TELEGRAM_TOKEN, DB_URI, float(THRESHOLD),
    learning=False, answering=True)
