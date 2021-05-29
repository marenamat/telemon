import sys
import socket
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

class TelegramBot:
    def __init__(self, name=socket.gethostname()):
        self.name = name

        # Load token from a private file. Only first line is used, anything else is ignored
        try:
            tokenfile = open("telegram.token", "r")
            self.token = tokenfile.read().rstrip()
            tokenfile.close()
        except Exception as e:
            print(f"Couldn't load Telegram token: {e}")
            sys.exit(2)

        self.updater = Updater(token=self.token, use_context=True)

        self.updater.dispatcher.add_handler(CommandHandler('start', lambda u, c: c.bot.send_message(chat_id=u.effective_chat.id, text=f"This is TeleMon instance at {self.name}.")))
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), lambda u, c: c.bot.send_message(chat_id=u.effective_chat.id, text=f"You wrote: {u.message.text}")))

        print(f'Loaded a Telegram Bot with token {self.token}')

    def run(self):
        self.updater.start_polling()

TelegramBot().run()
