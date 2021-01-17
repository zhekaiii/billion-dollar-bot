# -*- coding: utf-8 -*-

# Telegram
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import Updater, Filters, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext

# QR Code
from pyzbar.pyzbar import decode

# System libraries
import os
from os import listdir
from os.path import isfile, join
from datetime import datetime

from io import BytesIO
from PIL import Image

from random import shuffle

from db import *

from pybot import test, ab, ic1_id, ic2_id

def help(update, context):
    # TODO: Help text for Station Masters
    chat_id = update.effective_chat.id
    if update.message.chat.type == 'private':
        if userexists(chat_id) and haveperms(chat_id, 3): # IC
            text = '/mainmenu - Brings up the main menu where you have master control over everything!\n'
            text += '/user &#60;username&#62; &#60;og/station&#62; &#60;clearance level&#62; - Changes the OG/Station and/or clearance level for the user. The user must be registered in the database!\n'
            text += 'Level 0: Freshie\n'
            text += 'Level 1: OGL\n'
            text += 'Level 2: Station Master\n\n'
            text += 'You can lock/unlock QR codes, +/- attempts for quizzes and riddles and +/- points for whichever OG you want.'
        elif userexists(chat_id) and haveperms(chat_id, 2): # Station Master
            text = '/mainmenu - Brings up the main menu where you interact with the bot!\n\n'
            text += 'When an OG arrives at your station, you have to mark their attendance via the main menu.\n\n'
            text += 'After they complete the station, you can pass or fail them via the main menu.'
        else:
            text = 'You can send me QR codes here for me to unlock for your OG!'
    elif update.message.chat.type == 'group':
        text = '''/start - Must be sent by the OGL to register the group chat into the database
/register - Brings up the register button to register yourselves into the database
/mainmenu - Brings up the main menu where you interact with the bot!

To send QR codes, do it via PM

Quizzes are MCQs with 2 attempts each

Riddles are mostly open ended and you have to <b>reply</b> to the respective messages to lock in your answer. After which, I will take some time to think to accept or reject your answer

For Station Games, you <b>must</b> attempt the station once you unlock the station. If there is another OG at the station, you will be added to the queue. If you are already in a queue, you will automatically be queued after you complete the previous station. You can choose to re-queue a station if you fail the first time.'''
    context.bot.sendMessage(update.message.chat.id, text, parse_mode = ParseMode.HTML)

def start(update, context):
    chat = update.effective_chat
    chat_id = chat.id
    user_id = update.effective_user.id
    type = chat.type
    if type == 'private' and not userexists(user_id):
        text = 'Welcome!' if not full_name(update.effective_user) else 'Welcome, {}!'.format(full_name(update.effective_user))
        text += ' Please register in your respective Telegram Group! PMs are only for scanning QR codes!'
    elif type == 'group':
        if not userexists(user_id):
            text = 'Only an authorized personel can do that!'
        else:
            og_id = getogfromperson(user_id)
            if not (getogchatid(og_id) != None and getogchatid(og_id) == chat_id):
                if getogchatid(og_id) and getogchatid(og_id) != chat_id:
                    text = f'Warning! Another group chat has been registered under OG {og_ab(og_id)}. Overriding. {getogchatid(og_id)}'
                elif getogfromgroup(chat_id) and getogfromgroup(chat_id) != og_id:
                    text = f'This group chat has been registered as OG {getogfromgroup(chat_id)}. Overriding.'
                    executescript(f'UPDATE OG SET chat_id = NULL WHERE id = {getogfromgroup(chat_id)}')
                elif getogchatid(og_id) is None:
                    text = 'Group chat registered successfully.'
                context.bot.sendMessage(chat_id, text)
            executescript(f'UPDATE OG SET chat_id = {chat_id} WHERE id = {og_id}')
            register(update, context)
            return
    context.bot.sendMessage(chat_id, text)

def register(update, context):
    chat = update.effective_chat
    chat_id = chat.id
    user_id = update.effective_user.id
    type = chat.type
    keyboard = None
    if type == 'private':
        text = 'This command only works in group chats!'
    elif userexists(user_id) and haveperms(user_id, 3):
        if update.message.text == '/register':
            return
        og = True if update.message.text == '/register ogl' else (False if update.message.text == '/register sm' else None)
        if og is None: return
        text = 'Click on the OG you\'re leading!' if og else 'Click on the station you are in charge of!'
        text += ' Remember to PM me /start first before you register or you won\'t be able to receive my messages!'
        markup = []
        for i in range(10 if og and ab else (4 if og else 2)):
            temp = []
            for j in range(1, 4 if og and ab else (5 if og else 6)):
                num = i * (10 if og and ab else (4 if og else 5)) + j
                temp.append(InlineKeyboardButton(str(og_ab(num) if og and ab else num), callback_data = f'register.{num}.{1 if og else 2}'))
            markup.append(temp)
        keyboard = InlineKeyboardMarkup(markup)
    elif not groupregistered(chat_id):
        start(update, context)
        return
    else:
        text = '''Click here to register your username in the system! Remember to PM me /start first before you register or you won\'t be able to receive my messages!

Anyone can run /register anytime to bring this button up again.'''
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton('Register!', callback_data = f'register.{getogfromgroup(chat_id)}.0')]]
        )
    context.bot.sendMessage(chat_id, text, reply_markup = keyboard)

def mainmenu(update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    keyboard = None
    if not (userexists(user_id) and haveperms(user_id, 2)): # OGL/Freshie or unregistered user
        if update.effective_chat.type == 'private':
            text = 'You can only do that in your group chat!'
        elif not groupregistered(chat_id):
            text = 'OGL, please type /start!'
        else:
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton('Favour Points', callback_data = 'points')],
                    [InlineKeyboardButton('Station Games', callback_data = 'game')],
                    [InlineKeyboardButton('Riddles', callback_data = 'riddle')],
                    [InlineKeyboardButton('Quizzes', callback_data = 'quiz')],
                ]
            )
            text = f'Hello, OG {og_ab(getogfromgroup(chat_id))}. What would you like to do?'
    elif not haveperms(user_id, 3): # Station Master
        if update.effective_chat.type == 'private':
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton('Check Queue', callback_data = 'checkqueue')],
                    [InlineKeyboardButton('Mark Attendance', callback_data = 'attendance')],
                    [InlineKeyboardButton('Pass/Fail an OG', callback_data = 'passfail')],
                ]
            )
            text = f'Hello, Station {getogfromperson(chat_id)} Master {full_name(update.effective_user)}. What would you like to do?'
    else: # Head
        markup = []
        for i in range(5):
            temp = []
            for j in range(1, 5):
                num = i * 4 + j
                temp.append(InlineKeyboardButton(str(num), callback_data = f'master.{num}'))
            markup.append(temp)
        keyboard = InlineKeyboardMarkup(markup)
        text = 'What do you need to do for which OG?'
    context.bot.sendMessage(chat_id, text, reply_markup = keyboard)

def button(update, context):
    #print(update.callback_query)
    chat_id = update.effective_chat.id
    user = update.effective_user
    og_id = getogfromgroup(chat_id) if update.effective_chat.type == 'group' else getogfromperson(chat_id)
    callback_data = update.callback_query['data']
    original_text = update.callback_query['message']['text'] or update.callback_query['message']['caption']
    if callback_data.startswith('register'):
        og_id = callback_data.split('.')[1]
        perms = callback_data.split('.')[2]
        if userexists(user.id) and perms == 0:
            text = 'You have already registered!'
        else:
            executescript(f'''DELETE FROM Member WHERE chat_id = {user.id};
            INSERT INTO Member (chat_id, og_id, perms) VALUES ({user.id}, {og_id}, {perms})''')
            text = 'You have successfully registered! '
            if perms == '0':
                text += f'You are from OG {og_ab(og_id)}!'
            elif perms == '1':
                text += f'You are the OGL of OG {og_ab(og_id)}!'
            elif perms == '2':
                text += f'You are the Station Master of Station {og_id}!'
            else:
                text += 'You are the big boss. You have Master Control!'
        context.bot.sendMessage(user.id, text)
        return
    if callback_data == 'nothing':
        return
    if callback_data.startswith('master'):
        if not (userexists(user.id) and haveperms(user.id, 3)):
            return
    try:
        context.bot.delete_message(chat_id, update.callback_query['message']['message_id'])
    except:
        pass
    if callback_data.startswith('master'):
        split = callback_data.split('.')
        og = int(split[1])
        markup = [[InlineKeyboardButton('Back', callback_data = 'mainmenu')]]
        if len(split) == 2:
            text = f'What do you want to do with OG {og_ab(og)}?'
            markup += [
                [InlineKeyboardButton('+/- Points', callback_data = f'{callback_data}.1')],
                [InlineKeyboardButton('Lock/Unlock QR', callback_data = f'{callback_data}.2')]
            ]
        else:
            markup = [[InlineKeyboardButton('Back', callback_data = f'{".".join(split[:-1])}')]]
            action = int(split[2])
            if action == 1: # +/- Points
                pts = getpoints(og)
                if len(split) == 3:
                    text = f'How many points? OG {og_ab(og)} now has {pts} Favour Points.'
                    markup += [
                        [InlineKeyboardButton('-1', callback_data = f'{callback_data}.-1'), InlineKeyboardButton('+1', callback_data = f'{callback_data}.1')],
                        [InlineKeyboardButton('-2', callback_data = f'{callback_data}.-2'), InlineKeyboardButton('+2', callback_data = f'{callback_data}.2')],
                        [InlineKeyboardButton('-5', callback_data = f'{callback_data}.-5'), InlineKeyboardButton('+5', callback_data = f'{callback_data}.5')]
                    ]
                elif len(split) == 4:
                    markup = [[InlineKeyboardButton('Back', callback_data = f'{".".join(split[:-2])}')]]
                    amt = int(split[3])
                    pts = amt + pts
                    pts = 0 if pts < 0 else pts
                    addpts(og, amt)
                    context.bot.sendMessage(chat_id, f'{"" if amt < 0 else "+"}{amt} Favour Points for OG {og_ab(og)}! They now have {pts} points!')
                    text = f'How many points? OG {og_ab(og)} now has {pts} Favour Points.'
                    markup += [
                        [InlineKeyboardButton('-1', callback_data = f'master.{og}.1.-1'), InlineKeyboardButton('+1', callback_data = f'master.{og}.1.1')],
                        [InlineKeyboardButton('-2', callback_data = f'master.{og}.1.-2'), InlineKeyboardButton('+2', callback_data = f'master.{og}.1.2')],
                        [InlineKeyboardButton('-5', callback_data = f'master.{og}.1.-5'), InlineKeyboardButton('+5', callback_data = f'master.{og}.1.5')]
                    ]
            elif action == 2: # Lock/Unlock
                if len(split) == 3:
                    text = 'Choose a category:'
                    markup += [
                        [InlineKeyboardButton('Station Games', callback_data = f'{callback_data}.1')],
                        [InlineKeyboardButton('Riddles', callback_data = f'{callback_data}.2')],
                        [InlineKeyboardButton('Quizzes', callback_data = f'{callback_data}.3')]
                    ]
                else:
                    cat = 'g' if split[3] == '1' else ('r' if split[3] == '2' else 'q')
                    if len(split) == 4:
                        for i in range(3 if cat == 'r' else 2):
                            temp = []
                            for j in range(1, 6):
                                num = i * 5 + j
                                temp.append(InlineKeyboardButton(f'{num}', callback_data = f'{callback_data}.{num}'))
                            markup.append(temp)
                        text = f'Which {["station", "riddle", "quiz"][int(split[3]) - 1]}?'
                    else:
                        id = int(split[4])
                        attempts = checkqr(og, f'{cat}{id}')
                        if len(split) == 5:
                            have_attempts = True if (cat != 'g' and (cat == 'q' or id in [1,2,3,4,9,11,13,14,15])) else False
                            text = f'What would you like to do for {["Station", "Riddle", "Quiz"][int(split[3]) - 1]} {id}? '
                            if have_attempts:
                                text += f'{attempts} attempt{"s" if attempts != 1 else ""} remaining.' if (attempts >= 0 and attempts < 100) else ('has been completed.' if attempts > 5 else 'is locked.')
                            if attempts == -1: # Locked
                                markup.append([InlineKeyboardButton('Unlock', callback_data = f'{callback_data}.unlock')])
                            if attempts < 100: # Not Completed
                                if have_attempts and attempts > -1:
                                    markup.append([InlineKeyboardButton('+1 Attempt', callback_data = f'{callback_data}.1')])
                                    if attempts > 0:
                                        markup[1].append(InlineKeyboardButton('-1 Attempt', callback_data = f'{callback_data}.-1'))
                                markup.append([InlineKeyboardButton('Complete', callback_data = f'{callback_data}.complete')])
                            if attempts > -1: # Unlocked / Completed
                                markup.append([InlineKeyboardButton('Lock', callback_data = f'{callback_data}.lock')])
                        else:
                            stuff = split[-1]
                            executescript(f'''DELETE FROM Member WHERE chat_id = {user.id};
                            INSERT INTO Member (chat_id, og_id, perms) VALUES ({user.id}, {og}, 3)''')
                            if stuff == 'unlock':
                                if cat == 'g':
                                    unlockgame(id, update, context)
                                elif cat == 'r':
                                    unlockriddle(id, update, context)
                                elif cat == 'q':
                                    unlockquiz(id, update, context)
                            elif stuff == 'lock':
                                if cat == 'g':
                                    clearqueue(og, id, context)
                                    games_queued = [i[0] for i in getqueueforog(og)]
                                    if games_queued:
                                        queue_game(og, games_queue[0], context)
                                executescript(f'UPDATE OG SET {cat}{id} = -1 WHERE id = {og}')
                                context.bot.sendMessage(chat_id, f'{["Station", "Riddle", "Quiz"][int(split[3]) - 1]} {id} for OG {og_ab(og)} locked!')
                            elif stuff == 'complete':
                                rewards = getrewards(f'{cat}{id}')
                                if cat == 'g':
                                    if attempts > -1:
                                        clearqueue(og, id, context)
                                        games_queued = [i[0] for i in getqueueforog(og)]
                                        if games_queued:
                                            queue_game(og, games_queue[0], context)
                                addpts(og, rewards)
                                executescript(f'UPDATE OG SET {cat}{id} = 100 WHERE id = {og}')
                                context.bot.sendMessage(chat_id, f'{["Station", "Riddle", "Quiz"][int(split[3]) - 1]} {id} for OG {og_ab(og)} completed!')
                            else:
                                amt = int(stuff)
                                attempts += amt
                                executescript(f'UPDATE OG SET {cat}{id} = {attempts} WHERE id = {og}')
                                context.bot.sendMessage(chat_id, f'{"" if amt < 0 else "+"}{amt} attempt for {["Station", "Riddle", "Quiz"][int(split[3]) - 1]} {id} for OG {og_ab(og)}!')
                            mainmenu(update, context)
                            return
        context.bot.sendMessage(chat_id, text, reply_markup = InlineKeyboardMarkup(markup))
    if callback_data == 'mainmenu':
        mainmenu(update, context)
    elif callback_data == 'points':
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('Back', callback_data = 'mainmenu')]])
        pts = getpoints(og_id)
        context.bot.sendMessage(chat_id, f'Your OG has {pts} Favour Points', reply_markup = keyboard)
    elif callback_data == 'riddle': # riddle menu
        markup = [[InlineKeyboardButton('Back', callback_data = 'mainmenu')]]
        for i in range(3):
            temp = []
            for j in range(1, 6):
                riddlenum = str(i * 5 + j)
                attempts = checkqr(og_id, 'r{}'.format(riddlenum))
                buttontext = '🔒' if attempts == -1 else ('✅' if attempts > 5 else ('❌' if attempts == 0 else riddlenum))
                temp.append(InlineKeyboardButton(buttontext, callback_data = 'nothing' if attempts == -1 else 'r{}'.format(riddlenum)))
            markup.append(temp)
        text = '''Choose a riddle!

🔒 = Locked
✅ = Answered Correctly
❌ = Ran out of attempts'''
        context.bot.sendMessage(chat_id, text, reply_markup = InlineKeyboardMarkup(markup))
    elif callback_data.startswith('r') and callback_data[1:].isnumeric(): # display riddle
        id = int(callback_data[1:])
        markup = [[InlineKeyboardButton('Back', callback_data = 'riddle')]]
        attempts = checkqr(getogfromgroup(chat_id), callback_data)
        if attempts == -1:
            context.bot.sendMessage(chat_id, 'You have not scanned the right QR code for that riddle.', reply_markup = InlineKeyboardMarkup(markup))
            return
        rewards = getrewards(f'r{id}')
        text = f'<u><b>Riddle {id}'
        if id in [1,2,3,4,9,11,13,14,15] and attempts < 100:
            text += f' (Attempts left: {attempts})'
        text += f' [{rewards} Point' + ('s' if rewards > 1 else '') + f']</b></u>\n\n{getquestion(f"r{id}")}'

        if attempts == 0 or attempts > 5:
            if id == 9:
                file_id = 'AgACAgUAAxkDAAIEPl_zCAt6Gnbwt0aMUAABFSeHiEVtpAACOKwxG-3nmVdhp2yhkTvWi-HFy2x0AAMBAAMCAANtAAPgxQUAAR4E' if test else 'AgACAgUAAxkDAAMEX_6KyY15c5BaYAwT8FUI9UvssEYAAomsMRtAtflXlQf_MyaQyBSVJcJvdAADAQADAgADbQADIisAAh4E'
                context.bot.send_photo(chat_id, file_id, text, reply_markup = InlineKeyboardMarkup(markup), parse_mode = ParseMode.HTML)
            else:
                context.bot.sendMessage(chat_id, text, reply_markup = InlineKeyboardMarkup(markup), parse_mode = ParseMode.HTML)
            return
        if id == 9:
            markup.append([InlineKeyboardButton('True', callback_data = 'correct.r9.True'), InlineKeyboardButton('False', callback_data = 'wrong.r9.False')])
            file_id = 'AgACAgUAAxkDAAIEPl_zCAt6Gnbwt0aMUAABFSeHiEVtpAACOKwxG-3nmVdhp2yhkTvWi-HFy2x0AAMBAAMCAANtAAPgxQUAAR4E' if test else 'AgACAgUAAxkDAAMEX_6KyY15c5BaYAwT8FUI9UvssEYAAomsMRtAtflXlQf_MyaQyBSVJcJvdAADAQADAgADbQADIisAAh4E'
            context.bot.send_photo(chat_id, file_id, text, reply_markup = InlineKeyboardMarkup(markup), parse_mode = ParseMode.HTML)
            return
        elif id == 11:
            markup += [
                [InlineKeyboardButton('1', callback_data = 'wrong.r11.1'), InlineKeyboardButton('2', callback_data = 'wrong.r11.2')],
                [InlineKeyboardButton('3', callback_data = 'correct.r11.3'), InlineKeyboardButton('4', callback_data = 'wrong.r11.4')],
                [InlineKeyboardButton('5', callback_data = 'wrong.r11.5'), InlineKeyboardButton('6', callback_data = 'wrong.r11.6')]
            ]
        else:
            text += '\n\nReply to this message to send your answer!'
        context.bot.sendMessage(chat_id, text, reply_markup = InlineKeyboardMarkup(markup), parse_mode = ParseMode.HTML)
    elif callback_data == 'quiz': #quiz menu
        markup = [[InlineKeyboardButton('Back', callback_data = 'mainmenu')]]
        for i in range(2):
            temp = []
            for j in range(1, 6):
                quiznum = str(i * 5 + j)
                attempts = checkqr(og_id, f'q{quiznum}')
                buttontext = '🔒' if attempts == -1 else ('✅' if attempts > 5 else ('❌' if attempts == 0 else quiznum))
                temp.append(InlineKeyboardButton(buttontext, callback_data = 'nothing' if attempts == -1 else f'q{quiznum}'))
            markup.append(temp)
        text = '''Choose a quiz!

🔒 = Locked
✅ = Answered Correctly
❌ = Ran out of attempts'''
        context.bot.sendMessage(chat_id, text, reply_markup = InlineKeyboardMarkup(markup))
    elif callback_data.startswith('q') and callback_data[1:].isnumeric(): # display quiz
        id = int(callback_data[1:])
        markup = [[InlineKeyboardButton('Back', callback_data = 'quiz')]]
        attempts = checkqr(getogfromgroup(chat_id), callback_data)
        if attempts == -1:
            context.bot.sendMessage(chat_id, 'You have not scanned the right QR code for that quiz.', reply_markup = InlineKeyboardMarkup(markup))
            return
        rewards = getrewards(f'q{id}')
        text = f'<u><b>Quiz {id} '
        text += f'(Attempts left: {attempts}) ' if attempts < 100 else ''
        text += f'[{rewards} Point' + ('s' if rewards > 1 else '') + f']</b></u>\n\n{getquestion(f"q{id}")}'
        if attempts == 0 or attempts > 5:
            if id == 7:
                file_id = 'AgACAgUAAxkDAAIEqV_zOliCZ7mYct7I01uzeaE-J8pTAALSrDEb7eeZV-cOO5gPgL7x157CbHQAAwEAAwIAA20AAyjSBQABHgQ' if test else 'AgACAgUAAxkDAAMCX_6Kr8CnjioZ51RdqI0BpIWJtNwAAoisMRtAtflX1eM3DFfUeaAHRiRtdAADAQADAgADbQADk4UCAAEeBA'
                context.bot.send_photo(chat_id, file_id, text, reply_markup = InlineKeyboardMarkup(markup), parse_mode = ParseMode.HTML)
            else:
                context.bot.sendMessage(chat_id, text, reply_markup = InlineKeyboardMarkup(markup), parse_mode = ParseMode.HTML)
            return

        choice_list = [
            ['$1','$2','$3','$4'],
            ['50c_F0w_2021', 'SOC_FOW_2021', '50C_FOW_2O21', '50c_FOW_2O21'],
            ['Waa Cow!', 'Pizza Hut', 'FairPrice Xpress', 'Bookhaven', 'Office of Admissions'],
            ['1975', '1980', '1998', '1988'],
            ['Lee Yat Bun', 'Sherman Dang', 'Teh Wen Yi', 'Roy Chua'],
            ['12', '32', '20', '24'],
            ['80', '60', '100', '120'],
            ['15', '25', '13', '23'],
            ['75', '68', '82', '72'],
            ['19', '21', '20', '22']
        ]
        choices = [InlineKeyboardButton(choice_list[id - 1][0], callback_data = f'correct.q{id}.{choice_list[id - 1][0]}')]
        choices += [InlineKeyboardButton(choice_list[id - 1][i], callback_data = f'wrong.q{id}.{choice_list[id - 1][i]}') for i in range(1,4)]
        shuffle(choices)
        markup.append(choices[:2])
        markup.append(choices[2:])

        if id == 7:
            context.bot.send_photo(chat_id, 'AgACAgUAAxkDAAIEqV_zOliCZ7mYct7I01uzeaE-J8pTAALSrDEb7eeZV-cOO5gPgL7x157CbHQAAwEAAwIAA20AAyjSBQABHgQ', text, reply_markup = InlineKeyboardMarkup(markup), parse_mode = ParseMode.HTML)
        else:
            context.bot.sendMessage(chat_id, text, reply_markup = InlineKeyboardMarkup(markup), parse_mode = ParseMode.HTML)
    elif callback_data.startswith('correct'):
        cat = callback_data.split('.')[1][0]
        id = int(callback_data.split('.')[1][1:])
        attempts = checkqr(og_id, f'{cat}{id}')
        if attempts > 5 or attempts == 0:
            return
        reward = getrewards(f'{cat}{id}')
        ans = callback_data.split('.')[2]
        executescript(f'UPDATE OG SET {cat}{id} = 100 WHERE id = {og_id}')
        addpts(og_id, reward)
        context.bot.sendMessage(chat_id, original_text)
        context.bot.sendMessage(chat_id, f'{ans} is correct! ✅\nYou got {reward} Favour Points and now have {getpoints(og_id)} points!')
        mainmenu(update, context)
    elif callback_data.startswith('wrong'):
        cat = callback_data.split('.')[1][0]
        id = int(callback_data.split('.')[1][1:])
        attempts = checkqr(og_id, f'{cat}{id}')
        if attempts > 5 or attempts == 0:
            return
        if (cat == 'r' and id in [1,2,3,4,9,11,13,14,15]) or cat == 'q':
            attempts = checkqr(getogfromgroup(chat_id), '{}{}'.format(cat, id)) - 1
            executescript('UPDATE OG SET {}{} = {} WHERE id = {}'.format(cat, id, attempts, og_id))
        ans = callback_data.split('.')[2]
        context.bot.sendMessage(chat_id, original_text)
        context.bot.sendMessage(chat_id, f'{ans} is wrong! 🙅🏻')
        if attempts == 0:
            context.bot.sendMessage(chat_id, 'You have run out of attempts!')
        mainmenu(update, context)
    elif callback_data.startswith('sendans'):
        id = callback_data.split('.')[1]
        answering_og = callback_data.split('.')[2]
        attempts = checkqr(answering_og, f'{cat}{id}')
        ans = f'<u>Riddle {id}</u>\n'
        ans += getquestion(f'{cat}{id}')
        ans += f'\nOG {og_ab(answering_og)}'
        ans += '\nAnswer: ' + original_text.split('\n')[1]
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton('Accept', callback_data = 'accept.{}.{}'.format(id, answering_og)),
            InlineKeyboardButton('Reject', callback_data = 'reject.{}.{}'.format(id, answering_og))
        ]])
        context.bot.sendMessage(ic1_id, ans, reply_markup = keyboard, parse_mode = ParseMode.HTML)
        context.bot.sendMessage(chat_id, original_text)
        context.bot.sendMessage(chat_id, 'Answer sent! Please wait for the response.')
        mainmenu(update, context)
    elif callback_data.startswith('accept'):
        id = int(callback_data.split('.')[1])
        answering_og = callback_data.split('.')[2]
        executescript('UPDATE OG SET r{} = 100 WHERE id = {}'.format(id, answering_og))
        pts = getrewards(f'r{id}')
        addpts(answering_og, pts)
        context.bot.sendMessage(chat_id, original_text + '\nAnswer accepted!')
        context.bot.sendMessage(getogchatid(answering_og), 'OG {}, your answer for Riddle {} has been accepted!'.format(og_ab(answering_og), id))
        context.bot.sendMessage(getogchatid(answering_og), f'You gained {pts} Favour Points, you now have {getpoints(answering_og)} points!')
    elif callback_data.startswith('reject'):
        id = int(callback_data.split('.')[1])
        answering_og = callback_data.split('.')[2]
        text = f'OG {og_ab(answering_og)}, your answer for Riddle {id} has been rejected! 😵'
        if id in [1,2,3,4,11,13,14,15]:
            attempts = checkqr(answering_og, f'r{id}') - 1
            executescript('UPDATE OG SET r{} = {} WHERE id = {}'.format(id, attempts, answering_og))
            text += f' You have {attempts} attempts left.'
        context.bot.sendMessage(chat_id, original_text + '\nAnswer rejected!')
        context.bot.sendMessage(getogchatid(answering_og), text)
    elif callback_data == 'checkqueue':
        station = og_id
        queue = getqueueforgame(station)
        text = '<b><u>Queue:</u></b> (Doesn\'t update automatically)\n\n'
        for og, priority in queue:
            text += f'OG {og_ab(og)}'
            if priority == 0:
                text += ' (Currently playing)'
            text += '\n'
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('Back', callback_data = 'mainmenu'), InlineKeyboardButton('Refresh', callback_data = 'checkqueue')]])
        context.bot.sendMessage(chat_id, text, reply_markup = keyboard, parse_mode = ParseMode.HTML)
    elif callback_data == 'attendance':
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('Back', callback_data = 'mainmenu')]])
        station = og_id
        queue = getqueueforgame(station)
        if queue:
            playing_og = queue[0][0]
            if queue[0][1] == 1:
                text = f'OG {og_ab(playing_og)} is now playing your station.'
                executescript(f'UPDATE Queue SET queue = 0, time = {now()} WHERE og_id = {playing_og} AND game_id = {station}')
            elif queue[0][1] == 0:
                text = f'OG {og_ab(playing_og)} is already playing your station!'
        else:
            text = 'There are no OGs queuing for your station!'
        context.bot.sendMessage(chat_id, text, reply_markup = keyboard)
    elif callback_data == 'passfail':
        markup = [[InlineKeyboardButton('Back', callback_data = 'mainmenu')]]
        station = og_id
        queue = getqueueforgame(station)
        if queue:
            if queue[0][1] == 0:
                text = f'Finish OG {og_ab(queue[0][0])}\'s session at your station?'
                markup.append([InlineKeyboardButton('Pass', callback_data = 'pass'), InlineKeyboardButton('Fail', callback_data = 'fail')])
            elif queue[0][1] != 0:
                text = 'You have not marked attendance for the first OG in your queue!'
        else:
            text = 'There are no OGs queuing for your station!'
        context.bot.sendMessage(chat_id, text, reply_markup = InlineKeyboardMarkup(markup))
    elif callback_data == 'pass':
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('Back', callback_data = 'mainmenu')]])
        station = og_id
        queue = getqueueforgame(station)
        playing_og = queue[0][0]
        reward = getrewards(f'g{station}')
        clearqueue(playing_og, station, context)
        addpts(playing_og, reward)
        executescript(f'UPDATE OG SET g{station} = 100 WHERE id = {playing_og}')
        context.bot.sendMessage(getogchatid(playing_og), f'You completed Station {station} and got {reward} Favour Points! You now have {getpoints(playing_og)} points!')
        context.bot.sendMessage(chat_id, f'OG {og_ab(playing_og)} passed!', reply_markup = keyboard)
        og_queue = getqueueforog(playing_og)
        if og_queue:
            queue_game(playing_og, og_queue[0][0], context)
    elif callback_data == 'fail':
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('Back', callback_data = 'mainmenu')]])
        station = og_id
        queue = getqueueforgame(station)
        playing_og = queue[0][0]
        clearqueue(playing_og, station, context)
        executescript(f'UPDATE OG SET g{station} = 2 WHERE id = {playing_og}')
        context.bot.sendMessage(getogchatid(playing_og), f'You failed to complete Station {station}... You can try again later by re-queuing for that station!')
        context.bot.sendMessage(chat_id, f'OG {og_ab(playing_og)} failed!', reply_markup = keyboard)
        og_queue = getqueueforog(playing_og)
        if og_queue:
            queue_game(playing_og, og_queue[0][0], context)
    elif callback_data == 'game': # games menu
        markup = [[InlineKeyboardButton('Back', callback_data = 'mainmenu')]]
        queue = getqueueforog(og_id)
        for i in range(2):
            temp = []
            for j in range(1, 6):
                game_id = i * 5 + j
                attempts = checkqr(og_id, f'g{game_id}')
                buttontext = '🔒' if attempts == -1 else ('✅' if attempts > 5 else ('‼️' if queue and queue[0][0] == game_id else f'{game_id}'))
                temp.append(InlineKeyboardButton(buttontext, callback_data = 'nothing' if attempts > 5 or attempts == -1 else f'g{game_id}'))
            markup.append(temp)
        text = '''Choose a station! Click on the station you are queuing for to view the queue. Click on a station you have failed to re-queue.

🔒 = Locked
✅ = Passed
‼️ = Currently queuing'''
        context.bot.sendMessage(chat_id, text, reply_markup = InlineKeyboardMarkup(markup))
    elif callback_data.startswith('g') and callback_data[1:].isnumeric():
        id = int(callback_data[1:])
        markup = [[InlineKeyboardButton('Back', callback_data = 'game')]]
        state = checkqr(getogfromgroup(chat_id), callback_data)
        if state == -1: # locked
            context.bot.sendMessage(chat_id, 'You have not scanned the right QR code for that quiz.', reply_markup = InlineKeyboardMarkup(markup))
            return
        rewards = getrewards(f'g{id}')
        own_queue = getqueueforog(og_id)
        station_queue = getqueueforgame(id)
        markup.append([InlineKeyboardButton('Refresh', callback_data = f'g{id}')])
        text = f'<u>Station {id}: {rewards} Points</u>\n'
        if station_queue:
            text += 'Current queue:\n\n'
            for og, priority in station_queue:
                temp = f'OG {og_ab(og)}'
                if priority == 0:
                    temp += ' (Currently playing)'
                if og == og_id:
                    temp = f'<b>{temp}</b>'
                text += temp + '\n'
        else:
            text = 'The queue is empty!'
        if own_queue: # if your queue has something
            if own_queue[0][0] == id: # you are queued for that station
                if state == 2:
                    markup[1].append(InlineKeyboardButton('Unqueue', callback_data = 'unqueue'))
        elif state == 2: # if your queue has nothing and you failed the staion before
            markup[1].append(InlineKeyboardButton('Queue', callback_data = f'queue.{id}'))
        context.bot.sendMessage(chat_id, text, reply_markup = InlineKeyboardMarkup(markup), parse_mode = ParseMode.HTML)
    elif callback_data == 'unqueue':
        game_id = getqueueforog(og_id)[0][0]
        clearqueue(og_id, game_id, context)
        context.bot.sendMessage(chat_id, f'Unqueued from Station {game_id}!')
        mainmenu(update, context)
    elif callback_data.startswith('queue'):
        game_id = int(callback_data.split('.')[1])
        queue_game(og_id, game_id, context)
        mainmenu(update, context)

def decode_qr(update, context):
    chat_id = update.message.chat_id
    if not userexists(chat_id):
        context.bot.sendMessage(chat_id, 'Please register yourself in your respective Telegram Group before you start sending QR codes!')
        return
    if not haveperms(chat_id, 1): # Level 0 cannot send QR codes
        context.bot.sendMessage(chat_id, 'Only OGLs can send me QR codes!')
        return
    if haveperms(chat_id, 2): # Level 2 clearance or higher means not in any OG, so no need scan QR code
        context.bot.sendMessage(chat_id, 'You don\'t belong to any OGs! You don\'t need to send me QR codes!')
        return
    if update.message.photo:
        id_img = update.message.photo[-1].file_id
    else:
        return

    foto = context.bot.getFile(id_img)

    new_file = context.bot.get_file(foto.file_id)
    new_file.download('qrcode.png')

    try:
        result = decode(Image.open('qrcode.png'))
        decoded = result[0].data.decode("utf-8")
        if decoded.startswith('RIDDLE'):
            unlockriddle(int(decoded[7:]), update, context)
        elif decoded.startswith('QUIZ'):
            unlockquiz(int(decoded[5:]), update, context)
        elif decoded.startswith('+'):
            unlockpts(int(decoded[1]), update, context)
        elif decoded.startswith('GAME'):
            unlockgame(int(decoded[5:]), update, context)
    except Exception as e:
        print(e)
        context.bot.sendMessage(chat_id=chat_id, text='Unable to detect QR code. Try retaking the picture!')
    os.remove("qrcode.png")

def addpts(og_id, amt):
    points = getpoints(og_id) + amt
    points = 0 if points < 0 else points
    executescript(f'UPDATE OG SET points = {points} WHERE id = {og_id}')

def unlockriddle(id, update, context):
    user_id = update.effective_user.id
    og_id = getogfromperson(user_id)
    og_chat = getogchatid(og_id)
    if id in [1,2,3,4,13,14,15]:
        attempts = 5
    elif id == 11:
        attempts = 2
    else:
        attempts = 1
    if checkqr(og_id, 'r{}'.format(id)) > -1:
        context.bot.sendMessage(user_id, 'You have already scanned this QR Code!')
        return
    executescript('UPDATE OG SET r{} = {} WHERE id = {}'.format(id, attempts, og_id))
    context.bot.sendMessage(user_id, f'Riddle {id} unlocked!')
    context.bot.sendMessage(og_chat, f'Riddle {id} unlocked!')

def unlockquiz(id, update, context):
    user_id = update.effective_user.id
    og_id = getogfromperson(user_id)
    og_chat = getogchatid(og_id)
    if checkqr(og_id, 'q{}'.format(id)) > -1:
        context.bot.sendMessage(user_id, 'You have already scanned this QR Code!')
        return
    executescript('UPDATE OG SET q{} = 2 WHERE id = {}'.format(id, og_id))
    context.bot.sendMessage(user_id, f'Quiz {id} unlocked!')
    context.bot.sendMessage(og_chat, f'Quiz {id} unlocked!')

def unlockpts(id, update, context):
    user_id = update.effective_user.id
    og_id = getogfromperson(user_id)
    og_chat = getogchatid(og_id)
    if checkqr(og_id, 'p{}'.format(id)) > -1:
        context.bot.sendMessage(user_id, 'You have already scanned this QR Code!')
        return
    amt = 1 if id <= 6 else (2 if id <= 12 else (3 if id <= 14 else 4))
    addpts(og_id, amt)
    executescript('UPDATE OG SET p{} = 1 WHERE id = {}'.format(id, og_id))
    context.bot.sendMessage(user_id, f'You gained {amt} Favour Points! Your OG now has {pts} points.')
    context.bot.sendMessage(og_chat, f'You gained {amt} Favour Points! Your OG now has {pts} points.')

def unlockgame(id, update, context):
    user_id = update.effective_user.id
    og_id = getogfromperson(user_id)
    og_chat = getogchatid(og_id)
    if checkqr(og_id, 'g{}'.format(id)) > -1:
        context.bot.sendMessage(user_id, 'You have already scanned this QR Code!')
        return
    executescript(f'UPDATE OG SET g{id} = 1 WHERE id = {og_id}')
    context.bot.sendMessage(user_id, f'Station Game {id} unlocked!')
    context.bot.sendMessage(og_chat, f'Station Game {id} unlocked!')
    queue_game(og_id, id, context)

def queue_game(og_id, game_id, context):
    og_chat = getogchatid(og_id)
    own_queue = list(filter(lambda x: x[1] != 2, getqueueforog(og_id)))
    q = 2 if own_queue else 1 # if you are already queued for something q = 2 else q = 1
    if q == 1:
        context.bot.sendMessage(og_chat, f'You have been queued for Station Game {game_id}!')
        queue = list(filter(lambda x: x[1] <= 1, getqueueforgame(game_id))) # only get the OGs actually queuing
        if len(queue) == 0:
            text = f'There are no OGs queued in front of you. Please head to {getquestion(f"g{game_id}")} immediately!'
            notifysm(og_id, game_id, context)
        else:
            text = 'There ' + ('is 1 OG ' if len(queue) == 1 else f'are {len(queue)} OGs ') + f'queued in front of you. The station will be located at {getquestion(f"g{game_id}")}. '
            text += 'I will inform you when there is only one OG left in front of you.' if len(queue) > 1 else ''
    else:
        text = f'You are already queuing for another station game. You will be placed in the queue once you clear your stations.'
    executescript(f'''DELETE FROM Queue WHERE og_id = {og_id} AND game_id = {game_id};
    INSERT INTO Queue (og_id, game_id, time, queue) VALUES ({og_id}, {game_id}, {now()}, {q})''')
    context.bot.sendMessage(og_chat, text)

def clearqueue(og_id, game_id, context):
    executescript(f'DELETE FROM Queue WHERE og_id = {og_id} AND game_id = {game_id}')
    queue = getqueueforgame(game_id)
    if len(queue):
        context.bot.sendMessage(getogchatid(queue[0][0]), f'The previous OG is finished with station {game_id}. Please make your way to {getquestion(f"g{game_id}")} immediately!')
    if len(queue) >= 1:
        context.bot.sendMessage(getogchatid(queue[1][0]), f'There is only one OG in front of you. Please slowly make your way to {getquestion(f"g{game_id}")}!')

def confirmans(update, context):
    chat_id = update.message.chat_id
    original_msg = update.message.reply_to_message
    original_text = original_msg.text
    try:
        first_word = original_text.split()[0]
        id = int(original_text.split()[1])
    except:
        return
    cat = first_word[0].lower()
    attempts = checkqr(getogfromgroup(chat_id), f'{cat}{id}')
    if attempts > 5 or attempts == -1:
        return
    if original_msg.from_user.id != context.bot.id or first_word not in ['Riddle', 'Quiz'] or attempts == 0 or attempts > 5:
        return
    context.bot.delete_message(chat_id, original_msg.message_id)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('Yes', callback_data = 'sendans.{}.{}'.format(id, getogfromgroup(chat_id))), InlineKeyboardButton('No', callback_data = '{}{}'.format(cat, id))]])
    context.bot.sendMessage(chat_id, 'Confirm answer for {} {}:\n{}'.format(first_word, id, update.message.text), reply_markup = keyboard)

def full_name(effective_user):
    first_name = effective_user.first_name
    last_name = effective_user.last_name
    if not (first_name and last_name):
        return first_name or last_name
    return ' '.join([first_name, last_name])

def notifysm(og_id, game_id, context):
    sm_chat_id = getsmchatid(game_id)
    context.bot.sendMessage(sm_chat_id, f'OG {og_ab(og_id)} is on the way.')

def now():
    return int(datetime.timestamp(datetime.now()))

def changeuser(update, context):
    chat_id = update.message.chat_id
    user_id = update.effective_user.id
    if not (userexists(user_id) and haveperms(user_id, 3)):
        return
    split = update.message.text.split(' ')
    if len(split) == 4: # /user {username} {new_og} {new_perms}
        if split[2].isnumeric() and split[3].isnumeric() and int(split[3]) in [0, 1, 2]:
            username = split[1].strip('@')
            for cid in getchatids():
                if username == context.bot.getChat(cid).username:
                    executescript(f'UPDATE Member SET og_id = {split[2]}, perms = {split[3]} WHERE chat_id = {cid}')
                    context.bot.sendMessage(chat_id, f'@{username} is now {"a member of OG" if split[3] == "0" else ("an OGL of OG" if split[3] == "1" else "the station master of station")} {og_ab(split[2]) if split[3] == "1" and ab else split[2]}!')
                    return
            context.bot.sendMessage(chat_id, f'@{username} does not exist in the database!')
            return
    context.bot.sendMessage(chat_id, 'Wrong parameters!')

def unlockall(update, context):
    for i in range(1, 16):
        unlockriddle(i, update, context)
    for i in range(1, 11):
        unlockquiz(i, update, context)

def freshie(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    executescript(f'''DELETE FROM Member WHERE chat_id = {user_id};
    INSERT INTO Member (chat_id, og_id, perms) VALUES ({user_id}, 1, 0)''')
    context.bot.sendMessage(update.effective_chat.id, 'You have level 0 clearance!')

def ogl(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    executescript(f'''DELETE FROM Member WHERE chat_id = {user_id};
    INSERT INTO Member (chat_id, og_id, perms) VALUES ({user_id}, 19, 1)''')
    context.bot.sendMessage(chat_id, 'You have level 1 clearance!')

def sm(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    executescript(f'''DELETE FROM Member WHERE chat_id = {user_id};
    INSERT INTO Member (chat_id, og_id, perms) VALUES ({user_id}, 2, 2)''')
    context.bot.sendMessage(update.effective_chat.id, 'You have level 2 clearance!')

def head(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    executescript(f'''DELETE FROM Member WHERE chat_id = {user_id};
    INSERT INTO Member (chat_id, og_id, perms) VALUES ({user_id}, 0, 3)''')
    context.bot.sendMessage(update.effective_chat.id, 'You have level 3 clearance!')
