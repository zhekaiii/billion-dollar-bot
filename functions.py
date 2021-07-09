# -*- coding: utf-8 -*-

# Telegram
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode, parsemode, replymarkup, InputMediaPhoto
from telegram.ext import Updater, Filters, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext

# For QR Code decoding
import requests
from base64 import b64decode
import io

# System libraries
import os
from os import listdir
from os.path import isfile, join
from datetime import datetime

from random import shuffle, choice

from db import *
from pybot import test, ic1_id, ic2_id, ic3_id, ic4_id, logger


def unstuck(update, context):
    un()


def help(update, context):
    # TODO: Help text for Station Masters
    chat_id = update.effective_chat.id
    if update.message.chat.type == 'private':
        if userexists(chat_id) and haveperms(chat_id, 3):  # IC
            text = '/mainmenu - Brings up the main menu where you have master control over everything!\n'
            text += '/user &#60;username&#62; &#60;og/station&#62; &#60;clearance level&#62; - Changes the OG/Station and/or clearance level for the user. The user must be registered in the database!\n'
            text += 'Level 1: OGL\n'
            text += 'Level 2: Station Master\n\n'
            text += 'You can lock/unlock QR codes, +/- attempts for quizzes and riddles and +/- points for whichever OG you want.'
        elif userexists(chat_id) and haveperms(chat_id, 2):  # Station Master
            text = '/mainmenu - Brings up the main menu where you interact with the bot!\n\n'
            text += 'When an OG arrives at your station, you have to mark their attendance via the main menu.\n\n'
            text += 'After they complete the station, you can pass or fail them via the main menu.'
        elif userexists(chat_id) and haveperms(chat_id, 1):  # OGL
            text = 'You can send me QR codes here for me to unlock for your OG!'
        else:
            text = 'Please interact with me via the group chat!'
    elif update.message.chat.type == 'group':
        text = '''/start - Must be sent by the OGL to register the group chat into the database
/register - Brings up the register button to register yourselves into the database
/mainmenu - Brings up the main menu where you interact with the bot!

Only OGLs can send me QR codes via PM!

Quizzes are MCQs with 2 attempts each

Riddles are mostly open ended and you have to <b>reply</b> to the respective messages to lock in your answer. After which, I will take some time to think to accept or reject your answer

For Station Games, you <b>must</b> attempt the station once you unlock the station. If there is another OG at the station, you will be added to the queue. If you are already in a queue, you will automatically be queued after you complete the previous station. You can choose to re-queue a station if you fail the first time.'''
    context.bot.sendMessage(update.message.chat.id,
                            text, parse_mode=ParseMode.HTML)


def start(update, context):
    chat = update.effective_chat
    chat_id = chat.id
    user_id = update.effective_user.id
    type = chat.type
    if type == 'private':
        if not userexists(user_id):
            text = 'Welcome!' if not full_name(
                update.effective_user) else f'Welcome, {full_name(update.effective_user)}!'
            text += ' Please await more instructions from your group chats!'
        else:
            text = 'If you\'re looking for the help text, it\'s /help.'
    elif type == 'group':
        if haveperms(user_id, 1) and (not haveperms(user_id, 2)):
            og_id, house_id, house_name, _ = getogfromperson(user_id)
            # if your og hasn't had a chatid or if your og chat id is another group
            if getogchatid(og_id, house_id) == None or getogchatid(og_id, house_id) != chat_id:
                # if your og chat id is another group
                if getogchatid(og_id, house_id) and getogchatid(og_id, house_id) != chat_id:
                    text = f'Warning! Another group chat has been registered under OG {shorten(og_id, house_name)}. Overriding. {getogchatid(og_id, house_id)}'
                # if your og chat id is registered as another OG, which shdnt happen
                elif getogfromgroup(chat_id) and getogfromgroup(chat_id) != (og_id, house_id, house_name):
                    old_og_id, old_house_id, old_house_name = getogfromgroup(
                        chat_id)
                    text = f'This group chat has been registered as OG {shorten(old_og_id, old_house_name)}. Overriding.'
                    executescript(
                        f'UPDATE OG SET chat_id = NULL WHERE id = {old_og_id} AND house_id = {old_house_id}')
                elif getogchatid(og_id, house_id) is None:
                    text = 'Group chat registered successfully.'
                executescript(
                    f'UPDATE OG SET chat_id = {chat_id} WHERE id = {og_id} AND house_id = {house_id}')
            else:
                text = 'You already did that! Perhaps you want to do /mainmenu instead?'
        else:
            text = 'You can\'t do that.'
    context.bot.sendMessage(chat_id, text)


def register(update, context):
    chat = update.effective_chat
    chat_id = chat.id
    user_id = update.effective_user.id
    type = chat.type
    keyboard = None
    if (not haveperms(user_id, 3)) or len(update.message.text.split(' ')) == 1 or update.message.text.split(' ')[1] not in ['ogl', 'sm']:
        return
    if type == 'private':
        text = 'This command only works in group chats!'
    else:
        og = update.message.text.split(' ')[1] == 'ogl'
        text = 'Click on the OG you\'re leading!' if og else 'Click on the station you are in charge of!'
        text += ' Remember to PM me /start first before you register or you won\'t be able to receive my confirmation message!'
        markup = []
        temp = []
        if og:
            for og_id, house_id, house_name in gethouses():
                temp.append(InlineKeyboardButton(
                    shorten(og_id, house_name), callback_data=f'register.{og_id}.{house_id}.1'))
                if og_id == 6:
                    markup.append(temp)
                    temp = []
        else:
            for game_id, game_title in getgames():
                temp.append(InlineKeyboardButton(
                    game_title, callback_data=f'register.{game_id}.2'))
                if game_id % 2 == 0:
                    markup.append(temp)
                    temp = []
        keyboard = InlineKeyboardMarkup(markup)
    context.bot.sendMessage(chat_id, text, reply_markup=keyboard)
    # hello


def mainmenu(update, context, message_id=None):  # Done?
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    keyboard = None
    if update.effective_chat.type == 'group':
        if not haveperms(user_id, 2):  # Unregistered user or head or OGL
            if not groupregistered(chat_id):
                if haveperms(user_id, 1):
                    start(update, context)
                    mainmenu(update, context)
                    return
                else:
                    text = 'OGL, please type /start!'
            else:
                og_id, _, house_name, og_name = getogfromgroup(chat_id)
                if not og_name:
                    og_name = f'{house_name} {og_id}'
                keyboard = InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton(
                            'Favour Points', callback_data='points')],
                        [InlineKeyboardButton(
                            'Station Games', callback_data='game')],
                        [InlineKeyboardButton(
                            'Riddles', callback_data='riddle')],
                        [InlineKeyboardButton(
                            'Quizzes', callback_data='quiz')],
                    ]
                )
                text = f'Hello, {house_name} {og_id}. What would you like to do?'
        else:
            text = "You can only do this via PM!"
    elif not haveperms(user_id, 2):  # OGL or unregistered user
        text = 'You can only do that in your group chat!'
    elif not haveperms(user_id, 3):  # Station Master
        *_, game_id, game_title, _ = getuser(user_id)
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(
                    'Check Queue', callback_data='checkqueue')],
                [InlineKeyboardButton(
                    'Mark Attendance', callback_data='attendance')],
                [InlineKeyboardButton(
                    'Pass/Fail an OG', callback_data='passfail')],
            ]
        )
        text = f'Hello, {game_title} Master {full_name(update.effective_user)}. What would you like to do?'
    else:  # Head
        markup = [[InlineKeyboardButton("Points by House", callback_data="disphouse"),
                   InlineKeyboardButton("Points in Descending Order", callback_data="dispdesc")]]
        temp = []
        for og_id, house_id, house_name in gethouses():
            temp.append(InlineKeyboardButton(
                shorten(og_id, house_name), callback_data=f'master.{og_id}.{house_id}'))
            if og_id == 6:
                markup.append(temp)
                temp = []
        keyboard = InlineKeyboardMarkup(markup)
        text = 'What do you need to do for which OG?'
    if message_id:
        context.bot.edit_message_text(
            text, chat_id, message_id, reply_markup=keyboard)
    else:
        context.bot.sendMessage(chat_id, text, reply_markup=keyboard)


def senduserid(update, context):  # Done
    user_id = update.effective_user.id
    username = update.effective_user.username
    context.bot.sendMessage(ic1_id, f'{user_id} @{username}')


def button(update, context):
    # print(update.callback_query)
    chat_id = update.effective_chat.id
    user = update.effective_user
    username = user.username
    if update.effective_chat.type == 'group':
        res = getogfromgroup(chat_id)
        og_id, house_id, house_name, og_name = res if res else (
            None, None, None, None)
    else:
        res = getuser(user.id)
        og_id, house_id, house_name, station_id, station_title, og_name = res if res else (
            None, None, None, None, None)
    if not og_name:
        og_name = f'{house_name} {og_id}'
    callback_data = update.callback_query['data']
    original_text = update.callback_query['message']['text'] or update.callback_query['message']['caption']
    message_id = update.callback_query['message']['message_id']

    if callback_data.startswith('register'):
        perms = int(callback_data.split('.')[-1])
        if perms == 1:
            og_id = int(callback_data.split('.')[1])
            house_id = int(callback_data.split('.')[2])

            executescript(f'''INSERT INTO Member (chat_id, og_id, house_id, perms) VALUES ({user.id}, {og_id}, {house_id}, {perms})
            ON CONFLICT (chat_id) DO UPDATE
            SET
                og_id = {og_id},
                house_id = {house_id},
                game_id = NULL,
                perms = 1
            ''')
            text = f'the OGL of {getogname(og_id, house_id)}!'
        elif perms == 2:
            game_id = int(callback_data.split('.')[1])
            executescript(f'''INSERT INTO Member (chat_id, game_id, perms) VALUES ({user.id}, {game_id}, {perms})
            ON CONFLICT (chat_id) DO UPDATE
            SET
                og_id = NULL,
                house_id = NULL,
                game_id = {game_id},
                perms = 2
            ''')
            text = f'the Station Master of {getgametitle(game_id)}!'
        context.bot.sendMessage(chat_id, f'@{username} is {text}')
        try:
            context.bot.sendMessage(user.id, f'You are {text}')
        except:
            pass
        return
    if callback_data == 'nothing':
        return
    if callback_data.startswith('master'):
        if not haveperms(user.id, 3):
            return
        split = callback_data.split('.')
        og = int(split[1])
        house_id = int(split[2])
        house_name = gethousename(house_id)
        markup = [[InlineKeyboardButton('Back', callback_data='mainmenu')]]
        if len(split) == 3:
            text = f'What do you want to do with {house_name} {og}?'
            markup += [
                [InlineKeyboardButton(
                    '+/- Points', callback_data=f'{callback_data}.1')],
                [InlineKeyboardButton(
                    'Lock/Unlock QR', callback_data=f'{callback_data}.2')]
            ]
        else:
            markup = [[InlineKeyboardButton(
                'Back', callback_data=f'{".".join(split[:-1])}')]]
            action = int(split[3])
            if action == 1:  # +/- Points
                pts = getpoints(og, house_id)
                if len(split) == 4:
                    text = f'How many points? {house_name} {og} now has {pts} Favour Points.'
                    markup += [
                        [InlineKeyboardButton('-1', callback_data=f'{callback_data}.-1'), InlineKeyboardButton(
                            '+1', callback_data=f'{callback_data}.1')],
                        [InlineKeyboardButton('-2', callback_data=f'{callback_data}.-2'), InlineKeyboardButton(
                            '+2', callback_data=f'{callback_data}.2')],
                        [InlineKeyboardButton('-5', callback_data=f'{callback_data}.-5'), InlineKeyboardButton(
                            '+5', callback_data=f'{callback_data}.5')]
                    ]
                elif len(split) == 5:
                    markup = [[InlineKeyboardButton(
                        'Back', callback_data=f'{".".join(split[:-2])}')]]
                    amt = int(split[4])
                    pts = amt + pts
                    pts = 0 if pts < 0 else pts
                    addpts(og, house_id, amt)
                    context.bot.sendMessage(
                        chat_id, f'{"" if amt < 0 else "+"}{amt} Favour Points for {house_name} {og}! They now have {pts} points!')
                    text = f'How many points? {house_name} {og} now has {pts} Favour Points.'
                    markup += [
                        [InlineKeyboardButton('-1', callback_data=f'{".".join(split[:-1])}.-1'), InlineKeyboardButton(
                            '+1', callback_data=f'{".".join(split[:-1])}.1')],
                        [InlineKeyboardButton('-2', callback_data=f'{".".join(split[:-1])}.-2'), InlineKeyboardButton(
                            '+2', callback_data=f'{".".join(split[:-1])}.2')],
                        [InlineKeyboardButton('-5', callback_data=f'{".".join(split[:-1])}.-5'), InlineKeyboardButton(
                            '+5', callback_data=f'{".".join(split[:-1])}.5')]
                    ]
            elif action == 2:  # Lock/Unlock
                if len(split) == 4:
                    text = 'Choose a category:'
                    markup += [
                        [InlineKeyboardButton(
                            'Station Games', callback_data=f'{callback_data}.1')],
                        [InlineKeyboardButton(
                            'Riddles', callback_data=f'{callback_data}.2')],
                        [InlineKeyboardButton(
                            'Quizzes', callback_data=f'{callback_data}.3')],
                        [InlineKeyboardButton(
                            'Points', callback_data=f'{callback_data}.4')]
                    ]
                else:
                    cat = 'g' if split[4] == '1' else (
                        'r' if split[4] == '2' else ('q' if split[4] == 3 else 'p'))
                    table = 'quiz' if cat == 'q' else (
                        'riddle' if cat == 'r' else ('game' if cat == 'g' else 'point'))
                    if cat == 'g':
                        games = getgames()
                    og_qr = getogqr(og, house_id, cat)
                    if len(split) == 5:
                        temp = []
                        for i, row in enumerate(og_qr):
                            if cat in 'rq':
                                unlocked, completed, attempts = row
                            elif cat == 'p':
                                unlocked = row
                            else:
                                unlocked, completed, first = row
                            buttonemoji = '🔒' if not unlocked else ('✅' if cat == 'p' or completed else (
                                '❌' if cat in 'rq' and attempts == 0 else ''))
                            if cat == 'g':
                                g = games.pop(0)
                                temp.append(InlineKeyboardButton(
                                    f'{g[1]} {buttonemoji}', callback_data=f'{callback_data}.{g[0]}'))
                                if i % 2:
                                    markup.append(temp)
                                    temp = []
                            else:
                                temp.append(InlineKeyboardButton(
                                    f'{i + 1} {buttonemoji}', callback_data=f'{callback_data}.{i + 1}'))
                                if i % 5 == 4:
                                    markup.append(temp)
                                    temp = []
                        text = f'Which {["station", "riddle", "quiz"][int(split[4]) - 1]}?'
                    else:
                        id = int(split[5])
                        if cat == 'p':
                            unlocked, attempts = og_qr[id - 1], None
                            completed = unlocked
                        elif cat == 'g':
                            [unlocked, completed, first], attempts = og_qr[id - 1], None
                        else:
                            unlocked, completed, attempts = og_qr[id - 1]
                        if len(split) == 6:
                            text = f'What would you like to do for {["Station", "Riddle", "Quiz", "Point"][int(split[4]) - 1]} {id}? '
                            if not unlocked:
                                text += 'It is locked.'
                                markup.append([InlineKeyboardButton(
                                    'Unlock', callback_data=f'{callback_data}.unlock')])
                            elif completed:  # unlocked and completed
                                text += f'It has been {"completed" if cat != "p" else "unlocked"}.'
                            else:  # unlocked and not completed
                                if attempts is not None:
                                    text += f'{attempts} attempt{"s" if attempts > 1 else ""} remaining.'
                                    markup.append([InlineKeyboardButton(
                                        '+1 Attempt', callback_data=f'{callback_data}.1')])
                                    if attempts > 0:
                                        markup[1].append(InlineKeyboardButton(
                                            '-1 Attempt', callback_data=f'{callback_data}.-1'))
                                markup.append([InlineKeyboardButton(
                                    'Complete', callback_data=f'{callback_data}.complete')])
                            if unlocked or completed:  # Unlocked / Completed
                                markup.append([InlineKeyboardButton(
                                    'Lock', callback_data=f'{callback_data}.lock')])
                        else:
                            stuff = split[-1]
                            if stuff == 'unlock':
                                if cat == 'g':
                                    unlockgame(id, og, house_id,
                                               user, context.bot)
                                elif cat == 'r':
                                    unlockriddle(id, og, house_id,
                                                 user, context.bot)
                                elif cat == 'q':
                                    unlockquiz(id, og, house_id,
                                               user, context.bot)
                                else:
                                    unlockpts(id, og, house_id,
                                              user, context.bot)
                            elif stuff == 'lock':
                                if cat == 'g':
                                    clearqueue(og, house_id, id, context)
                                executescript(f'''
                                UPDATE {table}_og 
                                SET unlocked = FALSE{", first = TRUE" if cat == "g" else ""}{", completed = FALSE" if cat != "p" else ""}
                                WHERE og_id = {og} AND house_id = {house_id} AND {table}_id = {id}
                                ''')
                                context.bot.sendMessage(
                                    chat_id, f'{["Station", "Riddle", "Quiz"][int(split[4]) - 1]} {id} for {house_name} {og} locked!')
                            elif stuff == 'complete':
                                context.bot.edit_message_text(
                                    "Hold on...", chat_id, message_id)
                                if unlocked and not completed:
                                    if cat == 'g':
                                        clearqueue(og, house_id, id, context)
                                    [[rewards, points]] = executescript(f'''
                                        UPDATE {table}_og SET completed = TRUE WHERE og_id = {og} AND house_id = {house_id} AND {table}_id = {id};
                                        WITH point_table AS (SELECT points as rewards from {table} WHERE id = {id})
                                        UPDATE og SET points = points + point_table.rewards FROM point_table
                                        WHERE id = {og} AND house_id = {house_id} RETURNING point_table.rewards, points;
                                    ''', True)
                                    what = getgametitle(id) if cat == 'g' else (
                                        f'Riddle {id}' if cat == 'r' else f'Quiz {id}')
                                    context.bot.sendMessage(
                                        getogchatid(og, house_id), f'You completed {what} and received {rewards} Favour points! You now have {points} points!')
                                context.bot.answer_callback_query(
                                    update.callback_query.id, f'{["Station", "Riddle", "Quiz"][int(split[4]) - 1]} {id} for {house_name} {og} completed!', show_alert=True)
                            else:  # + attempts
                                amt = int(stuff)
                                attempts += amt
                                executescript(
                                    f'UPDATE {table}_og SET attempts = attempts + amt WHERE og_id = {og} AND house_id = {house_id} AND {table}_id = {id}')
                                context.bot.answer_callback_query(
                                    update.callback_query.id, f'{"" if amt < 0 else "+"}{amt} attempt for {["Station", "Riddle", "Quiz"][int(split[3]) - 1]} {id} for {house_name} {og}!', show_alert=True)
                            mainmenu(update, context, message_id)
                            return
        context.bot.edit_message_text(
            text, chat_id, message_id, reply_markup=InlineKeyboardMarkup(markup))
    if callback_data == 'mainmenu':
        mainmenu(update, context, message_id)
    elif callback_data == 'points':
        context.bot.edit_message_text('Please wait...', chat_id, message_id)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton('Back', callback_data='mainmenu')]])
        pts = getpoints(og_id, house_id)
        context.bot.edit_message_text(
            f'Your OG has {pts} Favour Points', chat_id, message_id, reply_markup=keyboard)
    elif callback_data == 'riddle':  # riddle menu
        markup = [[InlineKeyboardButton('Back', callback_data='mainmenu')]]
        temp = []
        riddles = getogqr(og_id, house_id, 'r')
        for i, riddle in enumerate(riddles):
            riddlenum = i + 1
            unlocked, completed, attempts = riddle
            buttontext = '🔒' if not unlocked else (
                '✅' if completed else ('❌' if attempts == 0 else riddlenum))
            temp.append(InlineKeyboardButton(
                buttontext, callback_data='nothing' if not unlocked else 'r{}'.format(riddlenum)))
            if riddlenum % 5 == 0:
                markup.append(temp)
                temp = []
        text = '''Choose a riddle!

        🔒 = Locked
        ✅ = Answered Correctly
        ❌ = Ran out of attempts'''
        context.bot.edit_message_text(
            text, chat_id, message_id, reply_markup=InlineKeyboardMarkup(markup))
    # display riddle
    elif callback_data.startswith('r') and callback_data[1:].isnumeric():
        id = int(callback_data[1:])
        markup = [[InlineKeyboardButton('Back', callback_data='riddle')]]
        unlocked, completed, attempts = getogqr(og_id, house_id, 'r', id)
        qn, rewards, image_url, _ = getriddle(id)
        if not unlocked:
            context.bot.edit_message_text('You have not scanned the right QR code for that riddle.',
                                          chat_id, message_id, reply_markup=InlineKeyboardMarkup(markup))
            return
        text = f'<u><b>Riddle {id} (Attempts left: {attempts}) [{rewards} Point' + (
            's' if rewards > 1 else '') + f']</b></u>\n\n{qn}'
        if not completed:
            if id == 5:
                markup.append([InlineKeyboardButton('True', callback_data='correct.r5.True'),
                              InlineKeyboardButton('False', callback_data='wrong.r5.False')])
            elif id == 7:
                markup += [
                    [InlineKeyboardButton('1', callback_data='wrong.r7.1'), InlineKeyboardButton(
                        '2', callback_data='wrong.r7.2')],
                    [InlineKeyboardButton('3', callback_data='correct.r7.3'), InlineKeyboardButton(
                        '4', callback_data='wrong.r7.4')],
                    [InlineKeyboardButton('5', callback_data='wrong.r7.5'), InlineKeyboardButton(
                        '6', callback_data='wrong.r7.6')]
                ]
            else:
                text += '\n\nReply to this message to send your answer!'
        if image_url:
            text = image_url + '\n' + text
        context.bot.edit_message_text(text, chat_id, message_id, reply_markup=InlineKeyboardMarkup(
            markup), parse_mode=ParseMode.HTML, disable_web_page_preview=False)
    elif callback_data == 'quiz':  # quiz menu
        markup = [[InlineKeyboardButton('Back', callback_data='mainmenu')]]
        temp = []
        quizzes = getogqr(og_id, house_id, 'q')
        for i, quiz in enumerate(quizzes):
            quiznum = i + 1
            unlocked, completed, attempts = quiz
            buttontext = '🔒' if not unlocked else (
                '✅' if completed else ('❌' if attempts == 0 else quiznum))
            temp.append(InlineKeyboardButton(
                buttontext, callback_data='nothing' if not unlocked else 'q{}'.format(quiznum)))
            if quiznum % 5 == 0:
                markup.append(temp)
                temp = []
        text = '''Choose a quiz!

        🔒 = Locked
        ✅ = Answered Correctly
        ❌ = Ran out of attempts'''
        context.bot.edit_message_text(
            text, chat_id, message_id, reply_markup=InlineKeyboardMarkup(markup))
    # display quiz
    elif callback_data.startswith('q') and callback_data[1:].isnumeric():
        id = int(callback_data[1:])
        markup = [[InlineKeyboardButton('Back', callback_data='quiz')]]
        unlocked, completed, attempts = getogqr(og_id, house_id, 'q', id)
        if not unlocked:
            context.bot.edit_message_text('You have not scanned the right QR code for that quiz.',
                                          chat_id, message_id, reply_markup=InlineKeyboardMarkup(markup))
            return
        qn, *choice_list, image_url, rewards = getquiz(id)
        text = f'<u><b>Quiz {id} '
        text += f'(Attempts left: {attempts}) ' if not completed else ''
        text += f'[{rewards} Point' + \
            ('s' if rewards > 1 else '') + f']</b></u>\n\n{qn}'

        if attempts > 0:
            choices = [InlineKeyboardButton(
                choice_list[0], callback_data=f'correct.q{id}.{choice_list[0]}')]
            choices += [InlineKeyboardButton(
                choice, callback_data=f'wrong.q{id}.{choice}') for choice in choice_list[1:]]
            shuffle(choices)
            markup.append(choices[:2])
            markup.append(choices[2:])

        if image_url:
            text = image_url + '\n' + text
        context.bot.edit_message_text(text, chat_id, message_id, reply_markup=InlineKeyboardMarkup(
            markup), parse_mode=ParseMode.HTML, disable_web_page_preview=False)
    elif callback_data.startswith('correct'):
        cat = callback_data.split('.')[1][0]
        id = int(callback_data.split('.')[1][1:])
        unlocked, completed, attempts = getogqr(og_id, house_id, cat, id)
        table = {'q': 'quiz', 'r': 'riddle'}
        buttontext = {'q': 'Quizzes', 'r': 'Riddles'}
        if not unlocked:
            text = 'You do not have access to this!'
        elif attempts == 0:
            text = 'You are out of attempts!'
        elif completed:
            mainmenu(update, context, message_id)
            return
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Main Menu', callback_data='mainmenu'), InlineKeyboardButton(
            buttontext[cat], callback_data=table[cat])]])
        if not unlocked or attempts == 0:
            context.bot.edit_message_text(
                text, chat_id, message_id, reply_markup=markup)
        ans = '.'.join(callback_data.split('.')[2:])
        [[points]] = executescript(f'''
            UPDATE {table[cat]}_og SET completed = TRUE
            WHERE og_id = {og_id} AND house_id = {house_id} AND {table[cat]}_id = {id};
            UPDATE og SET points = points + (
                SELECT points FROM {table[cat]} WHERE id = {id}
            ) WHERE id = {og_id} AND house_id = {house_id}
            RETURNING points;
        ''', True)
        context.bot.edit_message_text(
            f'{ans} is correct! ✅\nYou now have {points} points!', chat_id, message_id, reply_markup=markup)
    elif callback_data.startswith('wrong'):
        cat = callback_data.split('.')[1][0]
        id = int(callback_data.split('.')[1][1:])
        table = {'q': 'quiz', 'r': 'riddle'}
        buttontext = {'q': 'Quizzes', 'r': 'Riddles'}
        unlocked, completed, attempts = getogqr(og_id, house_id, cat, id)
        if not unlocked:
            text = 'You do not have access to this!'
        elif attempts == 0:
            text = 'You are out of attempts!'
        elif completed:
            mainmenu(update, context, message_id)
            return
        markup = InlineKeyboardMarkup([[InlineKeyboardButton('Main Menu', callback_data='mainmenu'), InlineKeyboardButton(
            buttontext[cat], callback_data=table[cat])]])
        if not unlocked or attempts == 0:
            context.bot.edit_message_text(
                text, chat_id, message_id, reply_markup=markup)
        executescript(f'''
            UPDATE {table[cat]}_og SET attempts = attempts - 1 WHERE {table[cat]}_id = {id} AND og_id = {og_id} AND house_id = {house_id}
        ''')
        ans = '.'.join(callback_data.split('.')[2:])
        context.bot.edit_message_text(f'{ans} is wrong! 🙅🏻' + (
            ' You have run out of attempts!' if attempts == 1 else ''), chat_id, message_id, reply_markup=markup)
    elif callback_data.startswith('sendans'):
        og_markup = InlineKeyboardMarkup([[InlineKeyboardButton(
            'Riddles', callback_data='riddle'), InlineKeyboardButton('Main Menu', callback_data='mainmenu')]])
        id = int(callback_data.split('.')[1])
        answer = update.callback_query.message.reply_to_message.text
        unlocked, completed, attempts = getogqr(og_id, house_id, 'r', id)
        if attempts <= 0:
            context.bot.edit_message_text(
                'Sorry, you ran out of attempts!', chat_id, message_id, reply_markup=og_markup)
            return
        [qn, image_url] = executescript(f'''
            UPDATE riddle_og SET attempts = riddle_og.attempts - 1
            FROM riddle r
            WHERE riddle_id = {id} AND r.id = {id} AND og_id = {og_id} AND house_id = {house_id}
            RETURNING r.text, r.image_url
        ''', True)[0]
        ans = f'<u>Riddle {id}</u>\n'
        ans += qn
        ans += ('\n' + image_url) if image_url else ''
        ans += f'\n{house_name} {og_id}'
        ans += '\nAnswer: ' + answer
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                'Accept', callback_data=f'accept.{id}.{og_id}.{house_id}'),
            InlineKeyboardButton(
                'Reject', callback_data=f'reject.{id}.{og_id}.{house_id}')
        ]])
        if id < 5:
            context.bot.sendMessage(
                ic1_id, ans, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            #context.bot.sendMessage(ic2_id, ans, reply_markup = keyboard, parse_mode = ParseMode.HTML)
        else:
            # for testing purposes
            context.bot.sendMessage(
                ic2_id, ans, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            # context.bot.sendMessage(
            #     ic3_id, ans, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            #context.bot.sendMessage(ic4_id, ans, reply_markup = keyboard, parse_mode = ParseMode.HTML)
        context.bot.edit_message_text(
            'Answer sent! Please wait for the response.', chat_id, message_id, reply_markup=og_markup)
    elif callback_data.startswith('accept'):
        id = int(callback_data.split('.')[1])
        answering_og_id = int(callback_data.split('.')[2])
        answering_house_id = int(callback_data.split('.')[3])
        og_chat = getogchatid(answering_og_id, answering_house_id)
        [points, amt] = executescript(f'''
            UPDATE riddle_og SET completed = TRUE WHERE riddle_id = {id} AND og_id = {answering_og_id} AND house_id = {answering_house_id};
            UPDATE og o SET points = o.points + r.points FROM riddle r WHERE r.id = {id}
            AND o.id = {answering_og_id} AND o.house_id = {answering_house_id} RETURNING o.points, r.points;
        ''', True)[0]
        context.bot.edit_message_text(
            original_text + '\nAnswer accepted!', chat_id, message_id)
        mainmenu(update, context)
        context.bot.sendMessage(
            og_chat, f'{getogname(answering_og_id, answering_house_id)}, your answer for Riddle {id} has been accepted! You gained {amt} Favour Points, you now have {points} points!')
    elif callback_data.startswith('reject'):
        id = int(callback_data.split('.')[1])
        answering_og_id = int(callback_data.split('.')[2])
        answering_house_id = int(callback_data.split('.')[3])
        *_, attempts = getogqr(answering_og_id, answering_house_id, 'r', id)
        text = f'{getogname(answering_og_id, answering_house_id)}, your answer for Riddle {id} has been rejected! 😵 {attempts} attempts remain!'
        context.bot.edit_message_text(
            original_text + '\nAnswer rejected!', chat_id, message_id, parse_mode=ParseMode.HTML)
        context.bot.sendMessage(getogchatid(
            answering_og_id, answering_house_id), text)
    elif callback_data == 'checkqueue':
        context.bot.edit_message_text('Loading...', chat_id, message_id)
        queue = getqueueforgame(station_id)
        text = '<b><u>Queue:</u></b> (Doesn\'t update automatically)\n\n'
        for og, house_id, priority in queue:
            text += f'{gethousename(house_id)} {og}'
            if priority == 0:
                text += ' (Currently playing)'
            text += '\n'
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(
            'Back', callback_data='mainmenu'), InlineKeyboardButton('Refresh', callback_data='checkqueue')]])
        context.bot.edit_message_text(
            text, chat_id, message_id, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    elif callback_data == 'attendance':
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton('Back', callback_data='mainmenu')]])
        queue = getqueueforgame(station_id)
        if queue:
            playing_og, playing_house, priority = queue[0]
            if priority == 1:
                text = f'{gethousename(playing_house)} {playing_og} is now playing your station.'
                executescript(
                    f'UPDATE Queue SET queue = 0, time = DEFAULT WHERE og_id = {playing_og} AND house_id = {playing_house} AND game_id = {station_id}')
            elif priority == 0:
                text = f'{gethousename(playing_house)} {playing_og} is already playing your station!'
        else:
            text = 'There are no OGs queuing for your station!'
        context.bot.edit_message_text(
            text, chat_id, message_id, reply_markup=keyboard)
    elif callback_data == 'passfail':
        markup = [[InlineKeyboardButton('Back', callback_data='mainmenu')]]
        queue = getqueueforgame(station_id)
        if queue:
            og, house, priority = queue[0]
            if priority == 0:
                text = f'Finish {gethousename(house)} {og}\'s session at your station?'
                markup.append([InlineKeyboardButton(
                    'Pass', callback_data='pass'), InlineKeyboardButton('Fail', callback_data='fail')])
            elif priority != 0:
                text = 'You have not marked attendance for the first OG in your queue!'
        else:
            text = 'There are no OGs queuing for your station!'
        context.bot.edit_message_text(
            text, chat_id, message_id, reply_markup=InlineKeyboardMarkup(markup))
    elif callback_data == 'pass':
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton('Back', callback_data='mainmenu')]])
        queue = getqueueforgame(station_id)
        og, house, priority = queue[0]
        clearqueue(og, house, station_id, context)
        [points, reward, og_chat, house_name] = executescript(f'''
            UPDATE game_og SET completed = TRUE, first = FALSE WHERE game_id = {station_id} AND og_id = {og} AND house_id = {house};
            UPDATE og o SET points = o.points + g.points FROM game g, house h WHERE g.id = {station_id} AND o.id = {og} AND o.house_id = {house} AND h.id = {house}
            RETURNING o.points, g.points, o.chat_id, h.name
        ''', True)[0]
        context.bot.sendMessage(
            og_chat, f'You completed {station_title} and got {reward} Favour Points! You now have {points} points!')
        context.bot.edit_message_text(
            f'{house} {og} passed!', chat_id, message_id, reply_markup=keyboard)
    elif callback_data == 'fail':
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton('Back', callback_data='mainmenu')]])
        queue = getqueueforgame(station_id)
        og, house, priority = queue[0]
        [og_chat, house_name] = executescript(f'''
            UPDATE game_og SET first = FALSE WHERE og_id = {og} AND house_id = {house};
            SELECT chat_id, house.name FROM og JOIN house ON (og.house_id = house.id) WHERE og.id = {og} AND house_id = {house};
        ''', True)[0]
        clearqueue(og, house, station_id, context)
        context.bot.sendMessage(
            og_chat, f'You failed to complete {station_title}... You can try again later by re-queuing for that station!')
        context.bot.edit_message_text(
            f'{gethousename(house)} {og} failed!', chat_id, message_id, reply_markup=keyboard)
    elif callback_data == 'game':  # games menu
        markup = [[InlineKeyboardButton('Back', callback_data='mainmenu')]]
        queue = getqueueforog(og_id, house_id)
        games = executescript(f'''
            SELECT unlocked, completed, title FROM game_og
            JOIN game ON game_id = id
            WHERE og_id = {og_id} AND house_id = {house_id}
            ORDER BY id
        ''', True)
        temp = []
        for i, (unlocked, completed, title) in enumerate(games):
            buttontext = title + ' ' + ('🔒' if not unlocked else (
                '✅' if completed else ('‼️' if queue and queue[0][0] == i + 1 else '')))
            temp.append(InlineKeyboardButton(
                buttontext, callback_data='nothing' if completed or not unlocked else f'g{i + 1}'))
            if i % 2:
                markup.append(temp)
                temp = []
        text = '''Choose a station! Click on the station you are queuing for to view the queue. Click on a station you have failed to re-queue.

        🔒 = Locked
        ✅ = Passed
        ‼️ = Currently queuing'''
        context.bot.edit_message_text(
            text, chat_id, message_id, reply_markup=InlineKeyboardMarkup(markup))
    elif callback_data.startswith('g') and callback_data[1:].isnumeric():
        context.bot.edit_message_text('Loading...', chat_id, message_id)
        id = int(callback_data[1:])
        markup = [[InlineKeyboardButton(
            'Station Games', callback_data='game'), InlineKeyboardButton('Main Menu', callback_data='mainmenu')]]
        [unlocked, completed, first, title, rewards] = executescript(f'''
            SELECT unlocked, completed, first, title, points FROM game_og
            JOIN game ON game_id = id
            WHERE og_id = {og_id} AND house_id = {house_id} AND id = {id}
        ''', True)[0]
        if not unlocked:
            context.bot.edit_message_text('You have not scanned the right QR code for that quiz.',
                                          chat_id, message_id, reply_markup=InlineKeyboardMarkup(markup))
            return
        own_queue = getqueueforog(og_id, house_id)
        station_queue = getqueueforgame(id)
        markup.append([InlineKeyboardButton(
            'Refresh', callback_data=f'g{id}')])
        text = f'<u>{title}: {rewards} Points</u>\n'
        if station_queue:
            text += 'Current queue:\n\n'
            for og, house, priority in station_queue:
                temp = f'{gethousename(house)} {og}'
                if priority == 0:
                    temp += ' (Currently playing)'
                if og == og_id:
                    temp = f'<b>{temp}</b>'
                text += temp + '\n'
        else:
            text = 'The queue is empty!'
        if own_queue:  # if your queue has something
            if own_queue[0][0] == id:  # you are queued for that station
                # if priority != 0 means you're queuing for it but not playing it
                if own_queue[0][1] != 0 and not first:
                    markup[1].append(InlineKeyboardButton(
                        'Unqueue', callback_data='unqueue'))
        else:  # if your queue has nothing so if it's unlocked you failed it before
            markup[1].append(InlineKeyboardButton(
                'Queue', callback_data=f'queue.{id}'))
        context.bot.edit_message_text(text, chat_id, message_id, reply_markup=InlineKeyboardMarkup(
            markup), parse_mode=ParseMode.HTML)
    elif callback_data == 'unqueue':
        context.bot.edit_message_text('Hold on...', chat_id, message_id)
        game_id = getqueueforog(og_id, house_id)[0][0]
        clearqueue(og_id, house_id, game_id, context)
        context.bot.edit_message_text(f'Unqueued from {getgametitle(game_id)}!', chat_id, message_id, reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton('Main Menu', callback_data='mainmenu')]]))
    elif callback_data.startswith('queue'):
        markup = [[InlineKeyboardButton('Back', callback_data='mainmenu')]]
        game_id = int(callback_data.split('.')[1])
        queue_game(og_id, house_id, game_id, None, chat_id, context.bot)
        context.bot.edit_message_text(
            f'Queued for {getgametitle(game_id)}!', chat_id, message_id, reply_markup=InlineKeyboardMarkup(markup))
    elif callback_data.startswith('disp'):
        house = callback_data == 'disphouse'
        pointslist = executescript(f"""
            SELECT og.id, house.name, og.name, points
            FROM og
            LEFT JOIN house ON (house.id = house_id)
            ORDER BY {'house.id, og.id' if house else 'points DESC'}
        """, True)
        txt = ""
        for i, row in enumerate(pointslist):
            og_id, house_name, og_name, points = row
            if i % 6 == 0:
                txt += "\n"
                if house:
                    txt += f"<b><u>House of {house_name}</u></b>\n"
            txt += f"{og_name if og_name else f'{house_name} {og_id}'}: {points} points\n"
        context.bot.edit_message_text(txt, chat_id, message_id, reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Main Menu", callback_data="mainmenu")]]), parse_mode=ParseMode.HTML)


def decodeforqr(message):
    return b64decode(message).decode("utf-8")


def sendcode(update, context):
    chat_id = update.message.chat_id
    message = update.message.text.split(" ")[1]
    if message == "":
        context.bot.sendMessage(
            chat_id, "Incorrect format. If the QR code message is ABCDE, type /decode ABCDE.")
        return
    try:
        decoded = decodeforqr(message)
    except:
        decoded = None
    decode_qr(update, context, decoded)


def sendpic(update, context):
    if update.message.photo:
        id_img = update.message.photo[-1].file_id
    else:
        return

    foto = context.bot.getFile(id_img)

    new_file = context.bot.get_file(foto.file_id)
    f = io.BytesIO()
    new_file.download(out=f)

    response = requests.post(
        'http://api.qrserver.com/v1/read-qr-code/?file',
        files={
            'file': f.getvalue()
        }
    )
    decoded = response.json()[0]['symbol'][0]['error'] or decodeforqr(
        response.json()[0]['symbol'][0]['data'])
    f.close()
    decode_qr(update, context, decoded)


def decode_qr(update, context, decoded):
    chat_id = update.message.chat_id
    og = getogfromperson(chat_id)
    og_id, house_id, *_ = [None, None, None] if og is None else og
    msg = context.bot.sendMessage(chat_id, 'Loading...')
    if update.message.caption != '/test':
        if not haveperms(chat_id, 1):  # Level 0 cannot send QR codes
            msg.edit_text('Only OGLs can send me QR codes!')
            return
        # Level 2 clearance or higher means not in any OG, so no need scan QR code
        if haveperms(chat_id, 2):
            msg.edit_text(
                'You don\'t belong to any OGs! You don\'t need to send me QR codes!')
            return
        if getogchatid(og_id, house_id) == None:
            msg.edit_text(
                'Please send /start in your group chat to register the group chat into the database!')
            return
        q = getqueueforog(og_id, house_id)
        if q and q[0][1] <= 1:
            gq = getqueueforgame(q[0][0])
            if gq[0][0] == og_id and gq[0][1] == house_id:
                msg.edit_text(
                    'Your OG is up next for a station game. You cannot scan QR codes!')
                return

    try:
        if decoded == None:
            raise NameError("Fail")
        elif decoded.startswith('RIDDLE'):
            unlockriddle(int(decoded[7:]), og_id, house_id,
                         update.effective_user, context.bot)
        elif decoded.startswith('QUIZ'):
            unlockquiz(int(decoded[5:]), og_id, house_id,
                       update.effective_user, context.bot)
        elif decoded.startswith('+'):
            unlockpts(int(decoded[1:]), og_id, house_id,
                      update.effective_user, context.bot)
        elif decoded.startswith('GAME'):
            unlockgame(int(decoded[5:]), og_id, house_id,
                       update.effective_user, context.bot)
        else:
            1/0
    except NameError:
        fun_text = [
            'Don\'t know how to take picture properly is it?',
            'Your phototaking skills need some work.',
            'You should really take up photography lessons.',
            'Are you sure you sent me a QR code?',
            'Is the lighting bad or is it just your skills?',
            'Is the camera bad or is it just your skills?',
            'A primary school kid can take better pictures than you.',
            'I guess I\'m just picky.',
            'Because you can\'t take pictures properly, -100 Favour Points! (Just kidding)',
            'I didn\'t ask for irrelevant pictures.',
            'Trash.'
        ]
        msg.edit_text(
            f'Unable to detect valid QR code. {choice(fun_text)} Please try again.')
        return
    except ZeroDivisionError:
        msg.edit_text(
            'Did you scan a SafeEntry QR code by mistake?')
        return
    except Exception as e:
        logger.warning(e)
        msg.edit_text(
            e)
        return
    msg.delete()


def addpts(og_id, house_id, amt):  # done
    p = executescript(
        f'UPDATE OG SET points = CASE WHEN points + {amt} > 0 THEN points + {amt} ELSE 0 END WHERE id = {og_id} AND house_id = {house_id} RETURNING points', True)
    return p[0][0]


def unlockriddle(riddle_id, og_id, house_id, user, bot):  # done
    og_chat = getogchatid(og_id, house_id)
    unlocked, *_ = getogqr(og_id, house_id, 'r', riddle_id)
    if unlocked:
        bot.sendMessage(user.id, 'You have already scanned this QR Code!')
        return
    executescript(f'''
        UPDATE riddle_og
        SET
            unlocked = TRUE,
            attempts = (
                SELECT attempts FROM riddle WHERE id = {riddle_id}
            )
        WHERE og_id = {og_id} AND house_id = {house_id} AND riddle_id = {riddle_id}
    ''')
    bot.sendMessage(user.id, f'Riddle {riddle_id} unlocked!')
    bot.sendMessage(og_chat, f'Riddle {riddle_id} unlocked!')


def unlockquiz(quiz_id, og_id, house_id, user, bot):  # done
    og_chat = getogchatid(og_id, house_id)
    unlocked, *_ = getogqr(og_id, house_id, 'q', quiz_id)
    if unlocked:
        bot.sendMessage(user.id, 'You have already scanned this QR Code!')
        return
    executescript(
        f'UPDATE quiz_og SET unlocked = TRUE, attempts = 2 WHERE og_id = {og_id} AND house_id = {house_id} AND quiz_id = {quiz_id}')
    bot.sendMessage(user.id, f'Quiz {quiz_id} unlocked!')
    bot.sendMessage(og_chat, f'Quiz {quiz_id} unlocked!')


def unlockpts(point_id, og_id, house_id, user, bot):  # done
    og_chat = getogchatid(og_id, house_id)
    [unlocked] = getogqr(og_id, house_id, 'p', point_id)
    if unlocked:
        bot.sendMessage(user.id, 'You have already scanned this QR Code!')
        return
    [amt] = getpoint(point_id)
    pts = addpts(og_id, house_id, amt)
    executescript(
        f'UPDATE point_og SET unlocked = TRUE WHERE og_id = {og_id} AND house_id = {house_id} AND point_id = {point_id}')
    bot.sendMessage(
        user.id, f'You gained {amt} Favour Points! Your OG now has {pts} points.')
    bot.sendMessage(
        og_chat, f'You gained {amt} Favour Points! Your OG now has {pts} points.')


def unlockgame(game_id, og_id, house_id, user, bot):  # done
    og_chat = getogchatid(og_id, house_id)
    unlocked, *_ = getogqr(og_id, house_id, 'g', game_id)
    if unlocked:
        bot.sendMessage(user.id, 'You have already scanned this QR Code!')
        return
    executescript(
        f'UPDATE game_og SET unlocked = TRUE WHERE og_id = {og_id} AND house_id = {house_id} AND game_id = {game_id}')
    game = getgame(game_id)
    bot.sendMessage(user.id, f'Station: {game[1]} unlocked!')
    bot.sendMessage(og_chat, f'Station: {game[1]} unlocked!')
    queue_game(og_id, house_id, game_id, game, og_chat, bot)


def queue_game(og_id, house_id, game_id, game, og_chat, bot):  # done
    own_queue = getqueueforog(og_id, house_id)
    if game_id == None and game == None:
        if not own_queue:
            return
        game_id = own_queue.pop(0)[0]
    if game == None:
        game = getgame(game_id)
    location, game_name, _ = game
    q = 2 if own_queue else 1  # if you are already queued for something q = 2 else q = 1
    if q == 1:
        bot.sendMessage(og_chat, f'You have been queued for {game_name}!')
        # only get the OGs actually queuing
        queue = list(filter(lambda x: x[2] <= 1, getqueueforgame(game_id)))
        if len(queue) == 0:
            text = f'There are no OGs queued in front of you. Please head to {location} immediately!'
            notifysm(og_id, house_id, game_id, bot)
        else:
            text = 'There ' + ('is 1 OG ' if len(queue) == 1 else f'are {len(queue)} OGs ') + \
                f'queued in front of you. The station will be located at {location}. '
            text += 'I will inform you when there is only one OG left in front of you.' if len(
                queue) > 1 else ''
    else:
        text = f'You are already queuing for another station game. You will be placed in the queue once you clear your stations.'
    executescript(f'''DELETE FROM Queue WHERE og_id = {og_id} AND house_id = {house_id} AND game_id = {game_id};
    INSERT INTO Queue (og_id, house_id, game_id, queue) VALUES ({og_id}, {house_id}, {game_id}, {q})''')  # TODO: Check if QR is unlocked first?
    bot.sendMessage(og_chat, text)


def clearqueue(og_id, house_id, game_id, context):  # TODO: LOOK AT THIS AGAIN
    deleted = executescript(
        f'DELETE FROM Queue WHERE og_id = {og_id} AND house_id = {house_id} AND game_id = {game_id} RETURNING *', True)
    if deleted == None:
        return
    og_chat = getogchatid(og_id, house_id)
    location, game_name, _ = getgame(game_id)
    queue_game(og_id, house_id, None, None, og_chat, context.bot)

    queue = getqueueforgame(game_id)
    if len(queue) and queue[0][2] == 1:
        context.bot.sendMessage(getogchatid(
            *queue[0][:2]), f'The previous OG is finished with the station {game_name}. Please make your way to {location} immediately!')
    if len(queue) >= 1 and queue[1][2] == 1:
        context.bot.sendMessage(getogchatid(
            *queue[1][:2]), f'There is only one OG in front of you. Please slowly make your way to {location}!')
    og_queue = getqueueforog(og_id, house_id)
    if og_queue:
        executescript(f'''
            UPDATE game_og SET queue = 1 WHERE og_id = {og_id} AND house_id = {house_id}
        ''')
    context.bot.sendMessage(
        og_chat, f"You have been queued for {getgametitle(game_id)}")


def confirmans(update, context):
    chat_id = update.message.chat_id
    og_id, house_id, house_name, og_name = getogfromgroup(chat_id)
    original_msg = update.message.reply_to_message
    original_text = original_msg.text
    if original_msg.from_user.username != ("zkthebot" if test else "nbdi_bot"):
        return
    try:
        first_word = original_text.split()[0]
        id = int(original_text.split()[1])
    except:
        return
    cat = first_word[0].lower()
    unlocked, completed, attempts = getogqr(og_id, house_id, cat, id)
    if not unlocked or completed or attempts == 0 or original_msg.from_user.id != context.bot.id or first_word not in ['Riddle', 'Quiz']:
        return
    context.bot.edit_message_reply_markup(
        chat_id, original_msg.message_id, reply_markup=None)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(
        'Yes', callback_data=f'''sendans.{id}'''), InlineKeyboardButton('No', callback_data=f'''{cat}{id}''')]])
    update.message.reply_text(
        f'Confirm answer for {first_word} {id}:\n{update.message.text}', reply_markup=keyboard)


def full_name(effective_user):
    first_name = effective_user.first_name
    last_name = effective_user.last_name
    if not (first_name and last_name):
        return first_name or last_name
    return ' '.join([first_name, last_name])


def notifysm(og_id, house_id, game_id, bot):
    sm_chat_id = getsmchatid(game_id)
    house_name = gethousename(house_id)
    bot.sendMessage(sm_chat_id, f'{house_name} {og_id} is on the way.')


def unlockall(update, context):
    og_id, house_id, *_ = getogfromgroup(update.effective_chat.id)
    executescript(f'''
        UPDATE riddle_og
        SET
            unlocked = TRUE,
            attempts = (
                SELECT attempts FROM riddle WHERE id = riddle_og.riddle_id
            )
        WHERE og_id = {og_id} AND house_id = {house_id} AND unlocked = FALSE;
        UPDATE quiz_og
        SET
            unlocked = TRUE,
            attempts = 2
        WHERE og_id = {og_id} AND house_id = {house_id} AND unlocked = FALSE;
    ''')
    context.bot.sendMessage(getogchatid(
        og_id, house_id), 'Unlocked everything!')


def sm(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    executescript(f'''DELETE FROM Member WHERE chat_id = {user_id};
    INSERT INTO Member (chat_id, og_id, perms) VALUES ({user_id}, 2, 2)''')
    context.bot.sendMessage(update.effective_chat.id,
                            'You have level 2 clearance!')


def head(update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    executescript(f'''DELETE FROM Member WHERE chat_id = {user_id};
    INSERT INTO Member (chat_id, og_id, perms) VALUES ({user_id}, 0, 3)''')
    context.bot.sendMessage(update.effective_chat.id,
                            'You have level 3 clearance!')
