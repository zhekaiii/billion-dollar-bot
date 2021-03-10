# -*- coding: utf-8 -*-

# Telegram
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, Filters, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext

# Telegram Functions
from functions import *

import os, logging
import psycopg2 as psql

test = 'config.py' in os.listdir()

if test:
	from config import *
else:
	TOKEN = os.environ['TELEGRAM_TOKEN']
	DB_URL = os.environ['DATABASE_URL']
	PORT = int(os.environ.get('PORT', 5000))

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

ic1_id = 129464681 #chat_id of Zhekai
ic2_id = 468173002 #chat_id of Jeremy

# database things
con = psql.connect(DB_URL, sslmode='prefer' if test else 'require')
cur = con.cursor()

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
	updater = Updater(TOKEN, request_kwargs={'read_timeout': 20, 'connect_timeout': 20}, use_context=True)
	dp = updater.dispatcher

	dp.add_handler(CommandHandler('start', start))
	dp.add_handler(CommandHandler('register', register))
	dp.add_handler(CommandHandler('mainmenu', mainmenu))
	dp.add_handler(CommandHandler('help', help))
	dp.add_handler(CommandHandler('user', changeuser))
	dp.add_handler(CommandHandler('senduserid', senduserid))
	dp.add_handler(MessageHandler(Filters.photo, decode_qr))
	dp.add_handler(MessageHandler(Filters.reply, confirmans))
	dp.add_handler(CallbackQueryHandler(button))

	# for debugging/testing purposes

	dp.add_handler(CommandHandler('reset', resetdb))
	dp.add_handler(CommandHandler('unlock', unlockall))
	dp.add_handler(CommandHandler('ogl', ogl))
	dp.add_handler(CommandHandler('sm', sm))
	dp.add_handler(CommandHandler('head', head))

	dp.add_error_handler(error)

	if test:
		updater.start_polling()
	else:
		updater.start_webhook(listen='0.0.0.0', port = PORT, url_path = TOKEN)
		updater.bot.setWebhook('https://quiet-tundra-35972.herokuapp.com/' + TOKEN)
	updater.bot.sendMessage(ic1_id, 'Up and running!')
	updater.idle()

if __name__ == '__main__':
	main()
