#!/usr/bin/python3

import configparser
import datetime
import logging
import os
import sys
import socket
import subprocess
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

config = configparser.ConfigParser()
try:
    config.read("telemon.conf")
except Exception as e:
    print(f"Couldn\'t load config: {str(e)}")
    sys.exit(2)

class SendQueue(FileSystemEventHandler):
    def __init__(self, dir, bot):
        super().__init__()

        self.dir = dir
        self.bot = bot

        self.observer = Observer()
        self.observer.schedule(self, self.dir + "/new", recursive=False)
        self.observer.start()

    def on_created(self, ev):
        p = ev.src_path.split("/")
        f = p.pop()
        pn = p.pop()
        if pn != "new":
            logging.error(f"Got a strange new file notification: {ev.src_path}")
            return

        p.append("old")
        p.append(f)

        nf = "/".join(p)

        ps = f.split(".")
        if len(ps) != 2:
            logging.error(f"Strange filename: {ev.src_path}")
            return

        if ps[1] == "txt":
            self.bot.send_msg(open(ev.src_path, "r").read())
            os.rename(ev.src_path, nf)
            return

        if ps[1] == "mp4":
            logging.info(f"Sending video: {ev.src_path}")
            self.bot.send_video(open(ev.src_path, "rb"))
            logging.info(f"Video sent: {ev.src_path}")
            os.rename(ev.src_path, nf)
            return

        logging.error(f"Unknown file type: {ev.src_path}")

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
        self.last_update = datetime.datetime.now()
        c.bot.edit_message_text(text=self.status_msg_text(), chat_id=self.chat_id, message_id=self.status_msg.message_id)
    def stop(self):
        self.status_updater.schedule_removal()

    def send_msg(self, msg):
        self.tbot.updater.bot.send_message(chat_id=self.chat_id, text=msg)

    def send_video(self, video):
        self.tbot.updater.bot.send_video(chat_id=self.chat_id, video=video)

class TryRunException(Exception):
    def __init__(self, cmd, code, stderr):
        self.cmd = cmd
        self.code = code
        self.stderr = stderr

    def __str__(self):
        return f"Running command `{' '.join(self.cmd)}` failed with code {self.code}: {self.stderr}"

class TelegramBot:
    def __init__(self, config, name):
        self.name = name
        self.config = config

        self.updater = Updater(token=config['Telegram']['token'], use_context=True)

        self.updater.dispatcher.add_handler(CommandHandler('start', self.cmd_start))
        self.updater.dispatcher.add_handler(CommandHandler('subscribe', self.cmd_subscribe))
        self.updater.dispatcher.add_handler(CommandHandler('unsubscribe', self.cmd_unsubscribe))
        self.updater.dispatcher.add_handler(CommandHandler('update', self.cmd_update))
        self.updater.dispatcher.add_handler(CommandHandler('reload', self.cmd_reload))
        self.updater.dispatcher.add_handler(CommandHandler('reply', self.cmd_reply))

        self.updater.dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), self.msg_echo))

        logging.info(f'Telegram bot startup')

        self.subs = []
        sstr = config.get('Telegram', 'subs', fallback=None)
        if sstr is not None and sstr != "":
            for s in sstr.split(','):
                self.subscribe(chat_id=int(s))

        self.sq = SendQueue(dir=config['SendQueue']['dir'], bot=self)

    def subscribe(self, chat_id):
        self.subs.append(TelegramSub(self, chat_id))

    def unsubscribe(self, ts):
        self.subs.remove(ts)
        ts.stop()

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

    def cmd_unsubscribe(self, u, c):
        for s in self.subs:
            if s.chat_id == u.effective_chat.id:
                self.unsubscribe(s)
                c.bot.send_message(chat_id=u.effective_chat.id, text=f"You have been unsubscribed.")
                self.update_config()
                return

        c.bot.send_message(chat_id=u.effective_chat.id, text=f"You have not been subscribed yet.")

    def tryshell(self, c, cmd):
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if p.returncode != 0:
            raise TryRunException(cmd, p.returncode, p.stderr)

        return p.stdout

    def cmd_update(self, u, c):
        try:
            cur = self.tryshell(c, ["git", "rev-parse", "HEAD"])
            curtext = self.tryshell(c, ["git", "show", "-q", "--oneline"])
            self.tryshell(c, ["git", "pull"])
            new = self.tryshell(c, ["git", "rev-parse", "HEAD"])
            newtext = self.tryshell(c, ["git", "show", "-q", "--oneline"])
        except TryRunException as e:
            c.bot.send_message(chat_id=u.effective_chat.id, text=f"Failed to update git: {str(e)}")
            return

        if cur == new:
            c.bot.send_message(chat_id=u.effective_chat.id, text=f"Git up to date at {curtext}")
        else:
            c.bot.send_message(chat_id=u.effective_chat.id, text=f"Git updated from {curtext} to {newtext}")

    def cmd_reload(self, u, c):
        self.tryshell(c, ["/bin/bash", "reloader.sh", str(os.getpid())])
        self.updater.stop()
        self.sq.observer.stop()
        self.sq.observer.join()
        sys.exit(0)

    def cmd_reply(self, u, c):
        if u.message.reply_to_message is not None:
            c.bot.send_message(chat_id=u.effective_chat.id, reply_to_message_id=u.message.reply_to_message.message_id, text=f"Reply test response")
        else:
            c.bot.send_message(chat_id=u.effective_chat.id, text=f"Error: Not a reply")

    def msg_echo(self, u, c):
        c.bot.send_message(chat_id=u.effective_chat.id, text=f"You wrote: {u.message.text}")

    def send_msg(self, msg):
        for s in self.subs:
            s.send_msg(msg)

    def send_video(self, video):
        for s in self.subs:
            s.send_video(video)

    def update_config(self):
        self.config['Telegram']['subs'] = ','.join(map(lambda s: str(s.chat_id), self.subs))
        with open('telemon.conf', 'w') as configfile:
            config.write(configfile)

TelegramBot(config=config, name=socket.gethostname()).run()
