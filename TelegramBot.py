import requests
import sys

# Load token from a private file. Only first line is used, anything else is ignored
try:
    tokenfile = open("telegram.token", "r")
    token = tokenfile.read().rstrip()
    tokenfile.close()
except Exception as e:
    print("Couldn't load Telegram token:", e)
    sys.exit(2)

# Just a testing API call
print("Token:", token)
response = requests.get('https://api.telegram.org/bot' + token + '/getMe')
print("Status:", response.status_code)
print("Response:", response.content)
