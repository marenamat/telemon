import requests
import sys

class TelegramBot:
    def __init__(self):
        # Load token from a private file. Only first line is used, anything else is ignored
        try:
            tokenfile = open("telegram.token", "r")
            self.token = tokenfile.read().rstrip()
            tokenfile.close()
        except Exception as e:
            print("Couldn't load Telegram token:", e)
            sys.exit(2)

        print("Loaded a Telegram Bot with token", self.token)

    def api(self, req):
        # Just a testing API call
        response = requests.get('https://api.telegram.org/bot' + self.token + '/' + req)
        print("Status:", response.status_code)
        print("Response:", response.content)

bot = TelegramBot()
bot.api("getMe")
