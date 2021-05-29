#!/usr/bin/python3

import configparser
import datetime
import logging
import sys
import socket
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

config = configparser.ConfigParser()
try:
    config.read("telemon.conf")
except Exception as e:
    print(f"Couldn\'t load config: {str(e)}")
    sys.exit(2)

logging.info("wat")

class Status:
    def __init__(self):
        self.startup = datetime.datetime.now()
        self.last_failure = None

status = Status()

class TelegramSub:
    def __init__(self, tbot, chat_id):
        self.tbot = tbot
        self.chat_id = chat_id

        self.subscribed_at = datetime.datetime.now()
        self.last_update = self.subscribed_at

        self.status_msg = self.tbot.updater.bot.send_message(chat_id=chat_id, text=self.status_msg_text())
#        self.tbot.updater.bot.pin_chat_message(chat_id=chat_id, message_id=self.status_msg.message_id)
        self.status_updater = self.tbot.updater.job_queue.run_repeating(self.status_update, interval=15, first=15)

    def status_msg_text(self):
        return f"""Startup:\t\t{status.startup}
Subscribed:\t{self.subscribed_at}
Last update:\t{self.last_update}"""

    def status_update(self, c):
        logging.info("in1")
        self.last_update = datetime.datetime.now()
        logging.info("in2")
        c.bot.edit_message_text(text=self.status_msg_text(), chat_id=self.chat_id, message_id=self.status_msg.message_id)
#        self.status_msg = c.bot.send_message(chat_id=self.chat_id, text=self.status_msg_text())
        logging.info("in3")

class TelegramBot:
    def __init__(self, config, name):
        self.name = name
        self.config = config

        self.updater = Updater(token=config['Telegram']['token'], use_context=True)

        self.updater.dispatcher.add_handler(CommandHandler('start', self.cmd_start))
        self.updater.dispatcher.add_handler(CommandHandler('subscribe', self.cmd_subscribe))
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), self.msg_echo))

        logging.info(f'Telegram bot startup')

        self.subs = []
        sstr = config.get('Telegram', 'subs', fallback=None)
        if sstr is not None:
            for s in sstr.split(','):
                self.subscribe(chat_id=int(s))

    def subscribe(self, chat_id):
        self.subs.append(TelegramSub(self, chat_id))

    def run(self):
        self.updater.start_polling()
        self.updater.idle()

    def cmd_start(self, u, c):
        c.bot.send_message(chat_id=u.effective_chat.id, text=f"This is TeleMon instance at {self.name}.")

    def cmd_subscribe(self, u, c):
        for s in self.subs:
            if s.chat_id == u.effective_chat.id:
                c.bot.send_message(chat_id=u.effective_chat.id, text=f"You are already subscribed.")
                return

        self.subscribe(u.effective_chat.id)
        self.update_config()

    def msg_echo(self, u, c):
        c.bot.send_message(chat_id=u.effective_chat.id, text=f"You wrote: {u.message.text}")

    def update_config(self):
        self.config['Telegram']['subs'] = ','.join(map(lambda s: str(s.chat_id), self.subs))
        with open('telemon.conf', 'w') as configfile:
            config.write(configfile)

TelegramBot(config=config, name=socket.gethostname()).run()
