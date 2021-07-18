
import requests
import json
import time as sleep
import telebot
import signal
import os
import threading

from datetime import *
from bs4 import BeautifulSoup

DELAY = 10 #sec

INFINITE_LOOP = False

bot = telebot.TeleBot('1819451029:AAFmiyWrdEZaxSSCXCrCsmGLrb5CvBVcAKI')
telegram_chats = {}

req_init = "https://tokyo-nakano-yoyaku.resv.jp/reserve/get_data.php?mode=init"

req_base = "https://tokyo-nakano-yoyaku.resv.jp/reserve/get_data.php?mode=maincalendar"
req_const = "&sp_id=4&res_num=0&sdt=&scroll_noheight=0&reserve_mode=&reserve_mode_user=&cancel_guest_hash="
req_year = "&t_year="
req_month = "&t_month="
req_day = "&t_day="
req_hosp= "&categ_id="
req_mp = "&mp_id="

clinics = {
56: "南中野区民活動センター",
57: "弥生区民活動センター",
58: "鍋横区民活動センター",
59: "東部区民活動センター",
60: "桃園区民活動センター",
61: "昭和区民活動センター",
62: "東中野区民活動センター",
63: "上高田区民活動センター",
64: "新井区民活動センター",
65: "江古田区民活動センター",
66: "沼袋区民活動センター",
67: "大和区民活動センター",
68: "鷺宮区民活動センター",
69: "上鷺宮区民活動センター",
70: "野方区民活動センター",
71: "中野区医師会館",
88: "河崎外科胃腸科",
89: "頭とからだのクリニック かねなか脳神経外科",
90: "中野ひだまりクリニック",
91: "東京警察病院",
92: "横畠病院",
93: "石森脳神経外科",
94: "たかのクリニック",
95: "のぐち内科クリニック",
96: "みやびハート＆ケアクリニック",
98: "塔ノ山医院",
99: "総合東京病院"
}

default_end_date = date(2021, 9, 1)
end_date = date(2021, 10, 1)
week = timedelta(days=7)

def make_request(year, month, day, hosp_id):
	curr_mp = hosp_id - 41 if hosp_id <= 71 else hosp_id - 56

	if hosp_id == 88:
		curr_mp -= 1

	req_addr = req_base
	req_addr += req_year + str(year)
	req_addr += req_month + str(month)
	req_addr += req_day + str(day)
	req_addr += req_hosp + str(hosp_id)
	req_addr += req_mp + str(curr_mp)
	req_addr += req_const

	init = json.loads(requests.get(req_init).content)

	if (init["init"] != "OK"):
		print("Warning: Init failed")

	response = requests.get(req_addr).content
	json_resp = json.loads(response)

	return json_resp["ret_html"]

def check_td(td):
	if td == None:
		False

	if td.get("id") == None:
		return False

	if not td.get("id").startswith('cal'):
		return False

	if len(td.findChildren('a')) > 0:
		return True

	if td.get("onlick") != None and td.get("onclick") != "":
		return True

	i = td.findChildren('i')

	for ch in i:
		if ch.get("class") != None:
			for cl in ch.get("class"):
				if cl.find("circle") != -1:
					return True
				if cl.find("triangle") != -1:
					return True

	return False

def find_free_dates(html):
	parsed_html = BeautifulSoup(html, features="html.parser")
	tds = parsed_html.find_all('td')

	res = []

	for td in tds:
		if check_td(td):
			td_date = td.get("id").split("_")[-1]
			year = int(td_date[:4])
			month = int(td_date[4:6])
			day = int(td_date[6:8])
			hour = int(td_date[8:10])
			mins = int(td_date[10:12])


			print(datetime(year, month, day, hour, mins))
			res.append(datetime(year, month, day, hour, mins))

	return res

def send_results(res, clinic):

	for d in res:
		message = "Place: " + clinic + "\n"
		message += "Time: " + d.strftime("%Y-%m-%d %H:%M")

		print(message)

		for user_id in telegram_chats.keys():
			deadline = telegram_chats[user_id]

			if d.date() <= deadline:
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
			curr_date = date.today()

			while curr_date <= end_date:
				for clinic_id in clinics.keys():
					if not INFINITE_LOOP:
						break

					html = make_request(curr_date.year, curr_date.month, curr_date.day, clinic_id)
					results = find_free_dates(html)

					if len(results) > 0:
						send_results(results, clinics[clinic_id])

				curr_date = curr_date + week

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
		start_message =  "Hello! I'm starting to check free reservations to vaccination in Nakano."
		start_message += "\n/check - check bot status\n/stop - stop bot"
		start_message += "\n/change_date - change end date"
		start_message += "\n/check_date - print end date"
		start_message += "\nEnd date by default - 2021-09-01"

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
	msg = bot.reply_to(message, "Please, enter new date in format <Year-Month-Day>")
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
