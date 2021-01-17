import sqlite3
from pybot import ic1_id, ic2_id, ab

db = 'db.sqlite'

'''
con = sqlite3.connect(db)
cur = con.cursor()
con.commit()
cur.close()
'''

def resetdb(a = None, b = None):
    global db
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.executescript('''

    DROP TABLE IF EXISTS House;
    DROP TABLE IF EXISTS OG;
    DROP TABLE IF EXISTS Member;
    DROP TABLE IF EXISTS Queue;

    CREATE TABLE Member (
        chat_id INTEGER NOT NULL PRIMARY KEY UNIQUE,
        og_id INTEGER,
        perms INTEGER DEFAULT 0
    );

    CREATE TABLE OG (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        chat_id INTEGER UNIQUE,
        house_id INTEGER,
        points INTEGER DEFAULT 0,
        r1 INTEGER DEFAULT -1,
        r2 INTEGER DEFAULT -1,
        r3 INTEGER DEFAULT -1,
        r4 INTEGER DEFAULT -1,
        r5 INTEGER DEFAULT -1,
        r6 INTEGER DEFAULT -1,
        r7 INTEGER DEFAULT -1,
        r8 INTEGER DEFAULT -1,
        r9 INTEGER DEFAULT -1,
        r10 INTEGER DEFAULT -1,
        r11 INTEGER DEFAULT -1,
        r12 INTEGER DEFAULT -1,
        r13 INTEGER DEFAULT -1,
        r14 INTEGER DEFAULT -1,
        r15 INTEGER DEFAULT -1,
        q1 INTEGER DEFAULT -1,
        q2 INTEGER DEFAULT -1,
        q3 INTEGER DEFAULT -1,
        q4 INTEGER DEFAULT -1,
        q5 INTEGER DEFAULT -1,
        q6 INTEGER DEFAULT -1,
        q7 INTEGER DEFAULT -1,
        q8 INTEGER DEFAULT -1,
        q9 INTEGER DEFAULT -1,
        q10 INTEGER DEFAULT -1,
        g1 INTEGER DEFAULT -1,
        g2 INTEGER DEFAULT -1,
        g3 INTEGER DEFAULT -1,
        g4 INTEGER DEFAULT -1,
        g5 INTEGER DEFAULT -1,
        g6 INTEGER DEFAULT -1,
        g7 INTEGER DEFAULT -1,
        g8 INTEGER DEFAULT -1,
        g9 INTEGER DEFAULT -1,
        g10 INTEGER DEFAULT -1,
        p1 INTEGER DEFAULT -1,
        p2 INTEGER DEFAULT -1,
        p3 INTEGER DEFAULT -1,
        p4 INTEGER DEFAULT -1,
        p5 INTEGER DEFAULT -1,
        p6 INTEGER DEFAULT -1,
        p7 INTEGER DEFAULT -1,
        p8 INTEGER DEFAULT -1,
        p9 INTEGER DEFAULT -1,
        p10 INTEGER DEFAULT -1,
        p11 INTEGER DEFAULT -1,
        p12 INTEGER DEFAULT -1,
        p13 INTEGER DEFAULT -1,
        p14 INTEGER DEFAULT -1,
        p15 INTEGER DEFAULT -1
    );

    CREATE TABLE House (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        name TEXT UNIQUE
    );

    CREATE TABLE Queue (
        og_id INTEGER,
        game_id INTEGER,
        time INTEGER,
        queue INTEGER
    );

    INSERT INTO House (name) VALUES ('Barg');
    INSERT INTO House (name) VALUES ('Etlas');
    INSERT INTO House (name) VALUES ('Aikon');
    INSERT INTO House (name) VALUES ('Scioc');
    INSERT INTO House (name) VALUES ('Trewitt')
    ''')

    for house_id in range(1, 6):
        for og in range(9):
            cur.execute(f'INSERT INTO OG (house_id) VALUES ({house_id})')
    for i in [ic1_id, ic2_id]:
        cur.execute(f'INSERT OR IGNORE INTO Member (chat_id, og_id, perms) VALUES ({i}, 0, 3)')

    con.commit()
    cur.close()
    resetqns()

def resetqns():
    points_list = {
        'g' : [5,7,7,5,5,5,8,5,5,5,7],
        'q' : [1,1,2,2,2,1,1,1,1,1],
        'r' : [2,1,2,2,2,1,1,3,2,2,1,2,1,1,1],
        'p' : [1,1,1,1,1,1,2,2,2,2,2,2,3,3,4]
    }
    riddles = [
        'Placeholder',
        'I have keys without key locks. I have space without rooms. You can enter but you cannot go outside. What am I?',
        'BreadTalk is Overrated i only go to ________',
        'Why is bread noisier than coffee?',
        'What question can you never answer yes to?',
        'A man got stuck in a room with two doors, one leads to a room of magnifying glass that magnifies the sun rays which would burn him, the other door leads to a dragon lair, how does he escape the room without dying?',
        '''In a mansion the owner of the house is murdered on a sunday morning. The inspector interviewed the gardener, the wife and the maid on what they are doing on the day of the murder.
The gardener answered “I was attending the garden”
The wife answered “I was in the kitchen preparing breakfast”
The maid answered “I was collecting mail”
On hearing the maid’s answer, the inspector immediately arrested the maid. Why?''',
        '''A burglar breaks into your house and holds your parents hostage. He tells you, “I will give you a chance to make a statement. If the statement is true, I will free your mother. If the statement is false, I will free your father. Then you will never see the other parent ever again. You cannot state a paradox or you will never see both parents again.” You say something and the burglar frees both parents. What was your statement?

Note: A paradox is a statement that contradicts itself''',
        'True or False: All of the balls in the bowl are blue',
        'The day before yesterday, Roy was 17. Next year, he will be 20. When is his birthday and what is today’s date?',
        'A family consists of two mothers, two daughters, one grandmother and one granddaughter. How many people are in the family?',
        '''Roy was watching television. Just after the midnight news here was a weather forecast: “It is raining now and will rain for the next 2 days. However, in 72 hours it will be bright and sunny.”
“Wrong again”, snorted Roy. He was correct but how did he know?''',
        'A mute SOC graduate walks into a bar. They had a sign that wrote “10 pints of beer” and showed it to the bartender. Why did they stop the bartender when the 3rd pint was served?',
        'I’m a rare case where today comes before yesterday. What am I?',
        'Where can you find the finest food in UTOWN?'
    ]
    quizzes = [
        'How much is this bowl of mala for 4 hungry pax?',
        'I heard of this hex-traordinary camp 3530635F4630775F32303231, I wonder what it is called.',
        'What is the store at #01-06, Stephen Riady Centre?',
        'Which year is the earliest the NUS School of Computing can trace its roots back to?',
        'Who is the president of NUS Computing Club?',
        'What is the maximum number of SU credits one can bring forward to Year 2?',
        'How many square roof panels are there in Frontier of UTown® shelter walkway?',
        '(((((5 * 2) + 6 / 2) * (8 - 4)) - 9 / 3) - 4) / 3',
        'How many POPStation lockers are there in Stephen Riady Centre?',
        'How many NUS utown beneficiaries are there?'
    ]
    locations = [
        'SRC Level 2 Balcony',
        'Outside Starbucks',
        'SRC Level 1, outside octobox',
        'SRC Level 1, outside auditorium',
        'SRC Level 2, outside Flavours',
        'Benches at SRC level 1',
        'Town Plaza',
        'ERC, outside Mac Commons',
        'ERC Level 1, near UTOWN benefactors',
        'SRC Level 2, outside Auditorium 2',
        'SRC Level 2, outside Flavours'
    ]
    executescript('''DROP TABLE IF EXISTS Question;
    CREATE TABLE Question (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        cat_id INTEGER,
        question_no INTEGER,
        display TEXT,
        points INTEGER
    );''')
    cat_id = 0
    for cat in ['g', 'q', 'r', 'p']:
        cat_id += 1
        rng = len(points_list[cat]) + 1
        for question_no in range(1, rng):
            if cat != 'p':
                display = riddles[question_no - 1] if cat == 'r' else (quizzes[question_no - 1] if cat == 'q' else locations[question_no - 1])
                executescript(f'INSERT INTO Question (cat_id, question_no, display, points) VALUES ({cat_id}, {question_no}, "{display}", {points_list[cat][question_no - 1]})')
            else:
                executescript(f'INSERT INTO Question (cat_id, question_no, points) VALUES ({cat_id}, {question_no}, {points_list[cat][question_no - 1]})')

def executescript(script):
    global db
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.executescript(script)
    con.commit()
    cur.close()

def getogfromperson(chat_id):
    global db
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute('''SELECT og_id FROM Member WHERE chat_id = {}'''.format(chat_id))
    res = cur.fetchone()
    cur.close()
    return res[0] if res else res

def getogfromgroup(chat_id):
    global db
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute('''SELECT id FROM OG WHERE chat_id = {}'''.format(chat_id))
    res = cur.fetchone()
    cur.close()
    return res[0] if res else res

def getpoints(og_id):
    global db
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute('''SELECT points FROM OG WHERE id = {}'''.format(og_id))
    res = cur.fetchone()
    cur.close()
    return res[0]

def checkqr(og_id, qr):
    global db
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute('SELECT {} FROM OG WHERE id = {}'.format(qr, og_id))
    res = cur.fetchone()
    cur.close()
    return res[0]

def userexists(chat_id):
    global db
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute('''SELECT chat_id from Member WHERE chat_id = {}'''.format(chat_id))
    res = cur.fetchall()
    cur.close()
    return res

def groupregistered(chat_id):
    global db
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute('''SELECT chat_id from OG WHERE chat_id = {}'''.format(chat_id))
    res = cur.fetchall()
    cur.close()
    return res

def getogchatid(og_id):
    global db
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute(f'SELECT chat_id FROM OG WHERE id = {og_id}')
    res = cur.fetchone()
    cur.close()
    return res[0] if res else res

def getsmchatid(game_id):
    global db
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute(f'SELECT chat_id FROM Member WHERE og_id = {game_id} AND perms = 2')
    res = cur.fetchone()
    cur.close()
    return res[0]

def haveperms(chat_id, level):
    global db
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute('''SELECT perms from Member WHERE chat_id = {}'''.format(chat_id))
    res = cur.fetchone()
    cur.close()
    return res[0] >= level if res else False

def getquestion(catandid):
    global db
    cat = catandid[0]
    id = int(catandid[1:])
    cat_id = ['g', 'q', 'r', 'p'].index(cat) + 1
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute(f'''SELECT display from Question WHERE cat_id = {cat_id} AND question_no = {id}''')
    res = cur.fetchone()
    cur.close()
    return res[0]

def getrewards(catandid):
    global db
    cat = catandid[0]
    id = int(catandid[1:])
    cat_id = ['g', 'q', 'r', 'p'].index(cat) + 1
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute(f'''SELECT points from Question WHERE cat_id = {cat_id} AND question_no = {id}''')
    res = cur.fetchone()
    cur.close()
    return res[0]

def getqueueforgame(game_id): # gets the queue of a specific station game
    global db
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute(f'''SELECT
        og_id, queue
    FROM Queue
    WHERE
        game_id = {game_id} AND (queue = 1 OR queue = 0)
    ORDER BY
        queue ASC,
        time ASC''')
    res = cur.fetchall()
    cur.close()
    return res

def getqueueforog(og_id): # gets the stations queued by an OG
    global db
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute(f'SELECT game_id, queue from Queue WHERE og_id = {og_id} ORDER BY queue ASC, time ASC')
    res = cur.fetchall()
    cur.close()
    return res

def getchatids():
    global db
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute(f'SELECT chat_id from Member')
    res = cur.fetchall()
    cur.close()
    return [i[0] for i in res]

def og_ab(og_id):
    number = (og_id + 1) // 2
    letter = 'A' if og_id % 2 else 'B'
    return f'{number}{letter}' if ab else f'{og_id}'
