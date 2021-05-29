#!/usr/bin/python3

import configparser
import logging
import sys
import socket
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

config = configparser.ConfigParser()
try:
    config.read("telemon.conf")
except Exception as e:
    print(f"Couldn\'t load config: {str(e)}")
    sys.exit(2)

logging.info("wat")

class TelegramBot:
    def __init__(self, token, name):
        self.name = name

        self.updater = Updater(token=token, use_context=True)

        self.updater.dispatcher.add_handler(CommandHandler('start', self.cmd_start))
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), self.msg_echo))

        logging.info(f'Loaded a Telegram Bot with token {token}')

    def run(self):
        self.updater.start_polling()

    def cmd_start(self, u, c):
        c.bot.send_message(chat_id=u.effective_chat.id, text=f"This is TeleMon instance at {self.name}.")

    def msg_echo(self, u, c):
        c.bot.send_message(chat_id=u.effective_chat.id, text=f"You wrote: {u.message.text}")

TelegramBot(token=config['Telegram']['token'], name=socket.gethostname()).run()
