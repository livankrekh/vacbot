import requests
import json
import time as sleep
import telebot
import signal
import os
import threading

from datetime import *
from dateutil.relativedelta import *
from bs4 import BeautifulSoup

DELAY = 10 #sec

INFINITE_LOOP = False

bot = telebot.TeleBot('1920663663:AAEXT1QFDzoMa0sDsK-3LEU_9sx9Sa3y_BQ')
telegram_chats = {}

req_base = "https://adachi.hbf-rsv.jp/mypage/status/?year=2021"
req_month = "&month="

regions = {
"c1": "舎人地区",
"c2": "鹿浜地区",
"c3": "伊興地区",
"c4": "西新井地区",
"c5": "竹の塚地区",
"c6": "花畑地区",
"c7": "保塚地区",
"c8": "中川地区",
"c9": "綾瀬地区",
"c10": "中央本町地区",
"c11": "梅田地区・梅島地区・関原地区",
"c12": "本木地区・扇地区",
"c13": "新田地区・江北地区・宮城地区",
"c14": "千住地区"
}

default_end_date = date(2021, 10, 1)
end_date = date(2022, 1, 1)
one_month = relativedelta(months=+1)

def make_request(month, region_id):
	if month > 12 or month < 1:
		return None

	req_addr = req_base
	req_addr += req_month + str(month)

	try:
		response = requests.get(req_addr).content
	except:
		print("Cannot get response from the server")
		return None

	return response

def check_td(td):
	span = td.findChildren("span" , recursive=False)

	if len(span) < 1:
		return False

	for s in span:
		text = s.getText()

		if text.find("人") != -1 and int(text[:-1]) > 1:
			return True

	return False

def find_free_dates(html, d, region_id):
	parsed_html = BeautifulSoup(html, features="html.parser")
	region_table = parsed_html.find("div", {"id": region_id})
	tables = region_table.find_all('table')

	res = []

	for table in tables:
		tds = table.findChildren("td")

		for i, td in enumerate(tds):
			if check_td(td):
				parent_div = None

				for p in td.parents:
					classes = p.get("class")

					if classes == None:
						continue

					if "couter" in classes:
						parent_div = p

				if parent_div == None:
					continue

				building = parent_div.find("strong", recirsive=False).getText()

				new_date = date(d.year, d.month, i+1)

				print("Found at", regions[region_id], ":", building, ",", new_date.strftime("%Y-%m-%d"))
				res.append((building, new_date))

	return res

def send_results(res, region):

	for building, d in res:
		message = "Place: " + region + " (" + building + ")" + "\n"
		message += "Time: " + d.strftime("%Y-%m-%d")

		print(message)

		for user_id in telegram_chats.keys():
			deadline = telegram_chats[user_id]

			if d <= deadline:
				bot.send_message(user_id, message)

def signal_exit(sig, frame):
	for chat_id in telegram_chats.keys():
		bot.send_message(chat_id, "Bot has been stopped by Livii. Please, contact to him or just wait!")
	os._exit(1)

def hard_exit():
	for chat_id in telegram_chats.keys():
		bot.send_message(chat_id, "Bot has been stopped by Livii. Please, contact to him or just wait!")
	os._exit(1)

def store_to_all(str_message):
	for chat_id in telegram_chats.keys():
		bot.send_message(chat_id, str_message)

def change_deadline(message):
	global telegram_chats

	text = message.text.split("-")

	if len(text) < 3:
		return

	try:
		new_date = date(int(text[-3]), int(text[-2]), int(text[-1]))
	except:
		return

	telegram_chats[message.chat.id] = new_date
	bot.send_message(message.chat.id, "End date changed to - " + new_date.strftime("%Y-%m-%d"))

def request_airstrike():
	global INFINITE_LOOP

	INFINITE_LOOP = True

	try:
		while INFINITE_LOOP:
			today = date.today()
			curr_date = date(today.year, today.month, 1)

			while curr_date <= end_date:
				for region_id in regions.keys():
					if not INFINITE_LOOP:
						break

					html = make_request(curr_date.month, region_id)

					if html == None:
						continue

					results = find_free_dates(html, curr_date, region_id)

					if len(results) > 0:
						send_results(results, regions[region_id])

				curr_date = curr_date + one_month

			sleep.sleep(DELAY)

		store_to_all("Bot finished loop! Please, press /start to restart bot.")

		INFINITE_LOOP = False

	except Error:
		INFINITE_LOOP = False
		print(Error)
		store_to_all("Bot has crashed. Please, press /start to restart bot or ask to Livii to relaunch bot!")

@bot.message_handler(commands=['start'])
def start_command(message):
	global telegram_chats

	if message.chat.id not in telegram_chats.keys():
		start_message =  "Hello! I'm starting to check free reservations to vaccination in Adachi."
		start_message += "\n/check - check bot status\n/stop - stop bot"
		start_message += "\n/change_date - change end date"
		start_message += "\n/check_date - print end date"
		start_message += "\nEnd date by default - " + default_end_date.strftime("%Y-%m-%d")

		telegram_chats[message.chat.id] = default_end_date
		bot.send_message(message.chat.id, start_message)
	else:
		bot.send_message(message.chat.id, "Bot is already running!")

@bot.message_handler(commands=['check'])
def check_command(message):
	if message.chat.id not in telegram_chats.keys():
		bot.send_message(message.chat.id, "Bot is not launched yet! Please, press /start to run.")
	else:
		bot.send_message(message.chat.id, "Bot is still running! Please wait for results.")

@bot.message_handler(commands=['stop'])
def stop_command(message):
	global telegram_chats

	if message.chat.id in telegram_chats.keys():
		del telegram_chats[message.chat.id]
		bot.send_message(message.chat.id, "Ok, Bot is stoping process of searching! To restart - press /start.")
	else:
		bot.send_message(message.chat.id, "Bot is not running now! You can run it by /start command.")

@bot.message_handler(commands=['change_date'])
def change_date(message):
	msg = bot.reply_to(message, "Please, enter new end date in format <Year-month-day>")
	bot.register_next_step_handler(msg, change_deadline)

@bot.message_handler(commands=['stop_bot'])
def stop_bot(message):
	global INFINITE_LOOP

	INFINITE_LOOP = False

@bot.message_handler(commands=['start_bot'])
def start_bot(message):
	thread = threading.Thread(target=request_airstrike, args=[])
	thread.start()

@bot.message_handler(commands=['check_bot'])
def check_bot(message):
	if INFINITE_LOOP:
		bot.send_message(message.chat.id, "Now bot inside the requests loop!")
	else:
		bot.send_message(message.chat.id, "Bot has a rest!")

@bot.message_handler(commands=['check_date'])
def check_date(message):
	user_id = message.chat.id

	if user_id in telegram_chats.keys():
		bot.send_message(user_id, "Current end date - " + telegram_chats[user_id].strftime("%Y-%m-%d"))
	else:
		bot.send_message(user_id, "Bot is not launched yet! Please, press /start to run the bot")

@bot.message_handler(commands=['deactivate_bot'])
def deactivate_command(message):
	hard_exit()

if __name__ == "__main__":
	signal.signal(signal.SIGINT, signal_exit)
	thread = threading.Thread(target=request_airstrike, args=[])
	thread.start()
	bot.polling()
