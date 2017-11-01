# coding: utf-8
""":mod:`autotweet.command` --- CLI interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides abillities to connect to telegram.

"""
from __future__ import unicode_literals

from datetime import timedelta
import logging
import os
import random
import re
import time

from pprint import pprint

import psutil

from six.moves import urllib

from telegram.ext import (
    BaseFilter, CommandHandler, Filters, MessageHandler, Updater)
from telegram.ext.dispatcher import run_async

from sysinfo import getsysinfo

from autotweet.learning import DataCollection, NoAnswerError
from autotweet.twitter import strip_tweet


INTERVAL = 60
CPU_THRESHOLD = 2.0
SECONDS = timedelta(days=1).total_seconds()


try:
    ADMIN_ID = int(os.getenv('ADMIN_ID'))
except TypeError:
    ADMIN_ID = None


class ReplyFilter(BaseFilter):
    def filter(self, message):
        return bool(message.reply_to_message)


Filters.reply = ReplyFilter()

logger = logging.getLogger(__name__)


class TelegramBot(object):
    def __init__(self, db_uri, token, threshold, learning=True, answering=True):
        self._make_updater(token)

        self.threshold = threshold
        self.data_collection = DataCollection(db_uri)

        self._init_handlers()
        if learning:
            self.enable_learning()
        if answering:
            self.enable_answering()

    def run(self):
        logger.info('Starting with {} documents.'.format(
            self.data_collection.get_count()))
        self.me = self.updater.bot.get_me()
        if ADMIN_ID:
            logger.info('Sending message to admin')
            self.updater.bot.send_message(
                chat_id=ADMIN_ID,
                text="I'm starting!"
            )
            self._update_last_activity()
        else:
            logger.info('Admin is not set')
        self.updater.start_polling()
        while True:
            try:
                time.sleep(INTERVAL)
                if self._is_over_threshold():
                    logger.info('Sending message')
                    self.updater.bot.send_message(
                        chat_id=ADMIN_ID,
                        text="Yo!"
                    )
                    self._update_last_activity()
            except KeyboardInterrupt:
                break
        # self.updater.idle()

    @run_async
    def learning_handler(self, bot, update):
        question = strip_tweet(update.message.reply_to_message.text)
        answer = strip_tweet(update.message.text, remove_url=False)
        self.data_collection.add_document(question, answer)

    @run_async
    def answering_handler(self, bot, update):
        question = strip_tweet(update.message.text)
        try:
            answer, ratio = self.data_collection.get_best_answer(question)
            if (ratio > self.threshold or
                    self._is_necessary_to_reply(bot, update)):
                logger.info('{} -> {}'.format(question, answer))
                update.message.reply_text(answer)
                self._update_last_activity()
        except NoAnswerError:
            logger.debug('No answer to {}'.format(update.message.text))
            if self._is_necessary_to_reply(bot, update):
                update.message.reply_text(r'¯\_(ツ)_/¯')
                self._update_last_activity()

    def leave_handler(self, bot, update):
        logger.info('Leave from chat {}'.format(update.message.chat_id))
        bot.leave_chat(update.message.chat_id)

    @run_async
    def sysinfo_handler(self, bot, update):
        update.message.reply_text(
            '```text\n{}\n```'.format(getsysinfo()),
            parse_mode='Markdown')
        self._update_last_activity()

    @run_async
    def photo_handler(self, bot, update):
        logger.info('Taking photo.')
        self._update_last_activity()
        try:
            req = urllib.request.urlopen('http://localhost:8080/photoaf.jpg')
        except:
            update.message.reply_text(
                'Unable to get photo'
            )
        else:
            update.message.reply_photo(
                photo=req)

    def debug_handler(self, bot, update):
        logger.info('Debugging')
        user = update.message.from_user
        pprint({
            'username': user.username,
            'id': user.id,
            'chat_id': update.message.chat_id,
        })

    def enable_learning(self):
        logger.debug('Enabling learning handler.')
        self.dispatcher.add_handler(
            MessageHandler(Filters.reply, self.learning_handler))

    def enable_answering(self):
        logger.debug('Enabling answer handler.')
        self.dispatcher.add_handler(
            MessageHandler(Filters.text, self.answering_handler))

    def _is_over_threshold(self):
        if not hasattr(self, 'last_activity'):
            self._update_last_activity()

        percent = psutil.cpu_percent()
        delta = time.time() - self.last_activity

        threshold = SECONDS / delta * percent / CPU_THRESHOLD
        logger.debug('CPU: {}, delta: {}, threshold: {}'.format(
            percent, delta, threshold))
        value = random.gauss(1.0, 0.1)

        return value > threshold

    def _update_last_activity(self):
        self.last_activity = time.time()

    def _make_updater(self, token):
        self.updater = Updater(token)
        self.dispatcher = self.updater.dispatcher

    def _init_handlers(self):
        self.dispatcher.add_handler(CommandHandler('leave', self.leave_handler))
        self.dispatcher.add_handler(
            CommandHandler('sysinfo', self.sysinfo_handler))
        self.dispatcher.add_handler(CommandHandler('photo', self.photo_handler))
        self.dispatcher.add_handler(CommandHandler('debug', self.debug_handler))

    def _is_necessary_to_reply(self, bot, update):
        message = update.message

        if message.chat.type == 'private':
            logger.debug('{} type private'.format(message.text))
            return True

        matched = re.search(r'@{}\b'.format(self.me.username), message.text)
        result = bool(matched)
        if result:
            logger.debug('{} mentioned me.'.format(message.text))
            return True

        return False


def start_bot(token, db_uri, threshold, learning=True, answering=True):
    bot = TelegramBot(db_uri, token, threshold, learning, answering)
    bot.run()
