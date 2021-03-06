import psycopg2 as psql
import csv
from pybot import ic1_id, ic2_id, cur, con, logger


def dropdb():
    cur.execute('''
    DROP TABLE IF EXISTS house CASCADE;
    DROP TABLE IF EXISTS og CASCADE;
    DROP TABLE IF EXISTS member;
    DROP TABLE IF EXISTS queue;
    DROP TABLE IF EXISTS quiz CASCADE;
    DROP TABLE IF EXISTS riddle CASCADE;
    DROP TABLE IF EXISTS game CASCADE;
    DROP TABLE IF EXISTS point CASCADE;
    DROP TABLE IF EXISTS quiz_og;
    DROP TABLE IF EXISTS riddle_og;
    DROP TABLE IF EXISTS game_og;
    DROP TABLE IF EXISTS point_og;

    CREATE TABLE house (
        id INTEGER NOT NULL PRIMARY KEY UNIQUE,
        name TEXT UNIQUE
    );

    CREATE TABLE og (
        id INTEGER NOT NULL,
        chat_id INTEGER UNIQUE,
        house_id INTEGER,
        points INTEGER DEFAULT 0,
        name TEXT DEFAULT NULL,

        UNIQUE (id, house_id),
        FOREIGN KEY (house_id) REFERENCES house(id)
    );

    CREATE TABLE quiz (
        id INTEGER NOT NULL PRIMARY KEY UNIQUE,
        text TEXT NOT NULL UNIQUE,
        answer TEXT NOT NULL,
        fake1 TEXT NOT NULL,
        fake2 TEXT NOT NULL,
        fake3 TEXT NOT NULL,
        image_url TEXT DEFAULT NULL,
        points INTEGER NOT NULL
    );

    CREATE TABLE riddle (
        id INTEGER NOT NULL PRIMARY KEY UNIQUE,
        text TEXT NOT NULL UNIQUE,
        points INT NOT NULL,
        image_url TEXT DEFAULT NULL,
        attempts INTEGER NOT NULL
    );

    CREATE TABLE point (
        id INTEGER NOT NULL PRIMARY KEY UNIQUE,
        points INTEGER NOT NULL
    );

    CREATE TABLE game (
        id INTEGER NOT NULL PRIMARY KEY UNIQUE,
        location TEXT NOT NULL,
        title TEXT NOT NULL UNIQUE,
        points INTEGER NOT NULL
    );

    CREATE TABLE member (
        chat_id INTEGER NOT NULL PRIMARY KEY UNIQUE,
        og_id INTEGER DEFAULT NULL,
        house_id INTEGER DEFAULT NULL,
        game_id INTEGER DEFAULT NULL,
        perms INTEGER NOT NULL,

        FOREIGN KEY (og_id, house_id) REFERENCES og(id, house_id),
        FOREIGN KEY (game_id) REFERENCES game(id)
    );

    CREATE TABLE queue (
        og_id INTEGER NOT NULL,
        house_id INTEGER NOT NULL,
        game_id INTEGER,
        time TIMESTAMP DEFAULT NOW(),
        queue INTEGER,

        UNIQUE (game_id, og_id, house_id),
        FOREIGN KEY (og_id, house_id) REFERENCES og(id, house_id),
        FOREIGN KEY (game_id) REFERENCES game(id)
    );

    CREATE TABLE game_og (
        game_id INTEGER NOT NULL,
        og_id INTEGER NOT NULL,
        house_id INTEGER NOT NULL,
        unlocked BOOLEAN NOT NULL DEFAULT FALSE,
        completed BOOLEAN NOT NULL DEFAULT FALSE,
        first BOOLEAN NOT NULL DEFAULT TRUE,

        UNIQUE (game_id, og_id, house_id),
        FOREIGN KEY (og_id, house_id) REFERENCES og(id, house_id),
        FOREIGN KEY (game_id) REFERENCES game(id)
    );

    CREATE TABLE quiz_og (
        quiz_id INTEGER NOT NULL,
        og_id INTEGER NOT NULL,
        house_id INTEGER NOT NULL,
        unlocked BOOLEAN NOT NULL DEFAULT FALSE,
        completed BOOLEAN NOT NULL DEFAULT FALSE,
        attempts INTEGER NOT NULL DEFAULT 2,

        UNIQUE (quiz_id, og_id, house_id),
        FOREIGN KEY (og_id, house_id) REFERENCES og(id, house_id),
        FOREIGN KEY (quiz_id) REFERENCES quiz(id)
    );

    CREATE TABLE riddle_og (
        riddle_id INTEGER NOT NULL,
        og_id INTEGER NOT NULL,
        house_id INTEGER NOT NULL,
        unlocked BOOLEAN NOT NULL DEFAULT FALSE,
        completed BOOLEAN NOT NULL DEFAULT FALSE,
        attempts INTEGER DEFAULT 0,

        UNIQUE (riddle_id, og_id, house_id),
        FOREIGN KEY (og_id, house_id) REFERENCES og(id, house_id),
        FOREIGN KEY (riddle_id) REFERENCES riddle(id)
    );

    CREATE TABLE point_og (
        point_id INTEGER NOT NULL,
        og_id INTEGER NOT NULL,
        house_id INTEGER NOT NULL,
        unlocked BOOLEAN NOT NULL DEFAULT FALSE,

        UNIQUE (point_id, og_id, house_id),
        FOREIGN KEY (og_id, house_id) REFERENCES og(id, house_id),
        FOREIGN KEY (point_id) REFERENCES point(id)
    )''')


def seeddb():
    with open('house.csv', encoding='latin-1') as f:
        rows = list(csv.reader(f, delimiter=','))
    header = rows.pop(0)
    for row in rows:
        cur.execute(f"""
            INSERT INTO house ({', '.join(header)})
            VALUES ({row[0]}, '{row[1]}')
        """)

    txt = ''
    for house_id in range(1, 7):
        for og in range(1, 7):
            txt += f"""INSERT INTO og (id, house_id) VALUES ({og}, {house_id});"""
    for i in [ic1_id, ic2_id]:
        txt += f'INSERT INTO member (chat_id, perms) VALUES ({i}, 3);'
    cur.execute(txt)

    resetqns()
    resetqr()


def un():
    con.rollback()


def getstats(day: int):
    houses = (1, 3, 4) if day == 1 else (
        (2, 5, 6) if day == 2 else (1, 2, 3, 4, 5, 6))
    cur.execute(f"""
        SELECT
            (SELECT COUNT(*) FROM riddle_og WHERE unlocked = TRUE AND house_id IN {houses}) AS unlocked_riddles,
            (SELECT COUNT(*) FROM riddle_og WHERE completed = TRUE AND house_id IN {houses}) AS completed_riddles,
            (SELECT COUNT(*) FROM quiz_og WHERE unlocked = TRUE AND house_id IN {houses}) AS unlocked_quizzes,
            (SELECT COUNT(*) FROM quiz_og WHERE completed = TRUE AND house_id IN {houses}) AS completed_quizzes,
            (SELECT COALESCE(SUM(attempts),0) FROM quiz_og WHERE house_id IN {houses}) AS quiz_attempts,
            (SELECT COUNT(*) FROM game_og WHERE unlocked = TRUE AND house_id IN {houses}) AS unlocked_games,
            (SELECT COUNT(*) FROM game_og WHERE completed = TRUE AND house_id IN {houses}) AS completed_games,
            (SELECT COUNT(*) FROM game_og WHERE completed = TRUE AND first = TRUE AND house_id IN {houses}) AS first_try_games,
            (SELECT COUNT(*) FROM point_og WHERE unlocked = TRUE AND house_id IN {houses}) AS unlocked_points,
            (SELECT SUM(points) FROM og WHERE house_id IN {houses}) AS total_points,
            (SELECT COUNT(*) FROM og WHERE house_id IN {houses}) AS og_count
    """)
    res = list(cur.fetchone())
    return res


def resetdb(update=None, context=None):
    if update.effective_chat.id != ic1_id:
        return
    msg = context.bot.sendMessage(update.effective_chat.id, "Hold on...")
    cur.execute(f'''
    UPDATE og SET chat_id = NULL, points = 0;
    DELETE FROM queue;
    UPDATE quiz_og SET attempts = 0, unlocked = FALSE, completed = FALSE;
    UPDATE riddle_og SET unlocked = FALSE, completed = FALSE, attempts = 0;
    UPDATE game_og SET unlocked = FALSE, completed = FALSE, first = TRUE;
    UPDATE point_og SET unlocked = FALSE;
    ''')
    con.commit()
    msg.edit_text("Reset Successful!")


def resetqns():
    with open('game.csv', encoding='latin-1') as f:
        rows = list(csv.reader(f, delimiter=','))
    header = rows.pop(0)
    txt = ''
    for row in rows:
        row = [r.replace("'", "''") for r in row]
        txt += f"""
            INSERT INTO game ({', '.join(header)})
            VALUES ({row[0]}, '{row[1]}', '{row[2]}', {row[3]})
            ON CONFLICT (id)
                DO UPDATE SET
                    {header[1]} = '{row[1]}',
                    {header[2]} = '{row[2]}',
                    {header[3]} = {row[3]}
                WHERE game.id = {row[0]};
        """

    with open('quiz.csv', encoding='latin-1') as f:
        rows = list(csv.reader(f, delimiter=','))
    header = rows.pop(0)
    for row in rows:
        row = [r.replace("'", "''") for r in row]
        txt += f"""
            INSERT INTO quiz ({', '.join(header)})
            VALUES ({row[0]}, '{row[1]}', '{row[2]}', '{row[3]}', '{row[4]}', '{row[5]}', {row[6]}, '{row[7]}', '{row[8]}')
            ON CONFLICT (id)
                DO UPDATE SET
                    {header[1]} = '{row[1]}',
                    {header[2]} = '{row[2]}',
                    {header[3]} = '{row[3]}',
                    {header[4]} = '{row[4]}',
                    {header[5]} = '{row[5]}',
                    {header[6]} = {row[6]},
                    {header[7]} = '{row[7]}',
                    {header[8]} = '{row[8]}'
                WHERE quiz.id = {row[0]};
        """

    with open('riddle.csv', encoding='latin-1') as f:
        rows = list(csv.reader(f, delimiter=','))
    header = rows.pop(0)
    for row in rows:
        row = [r.replace("'", "''") for r in row]
        txt += f"""
            INSERT INTO riddle ({', '.join(header)})
            VALUES ({row[0]}, '{row[1]}', {row[2]}, {row[3]}, '{row[4]}', '{row[5]}')
            ON CONFLICT (id)
                DO UPDATE SET
                    {header[1]} = '{row[1]}',
                    {header[2]} = {row[2]},
                    {header[3]} = {row[3]},
                    {header[4]} = '{row[4]}',
                    {header[5]} = '{row[5]}'
                WHERE riddle.id = {row[0]};
        """

    with open('point.csv', encoding='latin-1') as f:
        rows = list(csv.reader(f, delimiter=','))
    header = rows.pop(0)
    for row in rows:
        row = [r.replace("'", "''") for r in row]
        txt += f"""
            INSERT INTO point ({', '.join(header)})
            VALUES ({row[0]}, {row[1]})
            ON CONFLICT (id)
                DO UPDATE SET
                    {header[1]} = {row[1]}
                WHERE point.id = {row[0]};
        """
    cur.execute(txt)
    con.commit()


def resetqr(a=None, b=None):
    txt = ''
    for table in ['game', 'quiz', 'riddle', 'point']:
        txt += f"DELETE FROM {table}_og;"
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        for house_id in range(1, 7):
            for og_id in range(1, 7):
                for id in range(1, count + 1):
                    txt += f"INSERT INTO {table}_og ({table}_id, og_id, house_id) VALUES ({id}, {og_id}, {house_id});"
    cur.execute(txt)
    con.commit()


def executescript(script, returning=False):
    try:
        cur.execute(script)
        con.commit()
        if returning:
            return cur.fetchall()
    except Exception as e:
        con.rollback()
        print(e)
        return None


def getogfromperson(chat_id):
    cur.execute(
        f'''SELECT og_id, og.house_id, house.name, og.name FROM member JOIN og ON (og_id = og.id AND member.house_id = og.house_id) JOIN house ON (house.id = og.house_id) WHERE member.chat_id = {chat_id}''')
    res = cur.fetchone()
    return res


def getogfromgroup(chat_id):
    cur.execute(
        f'''SELECT og.id, house_id, house.name, og.name FROM og JOIN house ON (house.id = house_id) WHERE chat_id = {chat_id}''')
    res = cur.fetchone()
    return res


def getpoints(og_id: int, house_id: int):
    cur.execute(
        f'''SELECT points FROM og WHERE id = {og_id} AND house_id = {house_id}''')
    res = cur.fetchone()
    return res[0]


def userexists(chat_id):
    cur.execute(f'''SELECT chat_id from member WHERE chat_id = {chat_id}''')
    res = cur.fetchall()
    return res


def groupregistered(chat_id):
    cur.execute('''SELECT chat_id from og WHERE chat_id = {}'''.format(chat_id))
    res = cur.fetchall()
    return res


def getogchatid(og_id, house_id):
    cur.execute(
        f'SELECT chat_id FROM og WHERE id = {og_id} AND house_id = {house_id}')
    res = cur.fetchone()
    return res[0] if res else res


def getsmchatid(game_id):
    cur.execute(
        f'SELECT chat_id FROM member WHERE game_id = {game_id} AND perms = 2')
    res = cur.fetchone()
    return res[0]


def haveperms(chat_id, level):
    cur.execute(f'''SELECT perms from member WHERE chat_id = {chat_id}''')
    res = cur.fetchone()
    return (res[0] >= level if res else False)


def getquiz(id):
    cur.execute(f'SELECT * from quiz WHERE id = {id}')
    res = cur.fetchone()
    return res[1:]


def getriddle(id):
    cur.execute(f'SELECT * from riddle WHERE id = {id}')
    res = cur.fetchone()
    return res[1:]


def getgame(id):
    cur.execute(f'SELECT * from game WHERE id = {id}')
    res = cur.fetchone()
    return res[1:]


def getpoint(id):
    cur.execute(f'SELECT * from point WHERE id = {id}')
    res = cur.fetchone()
    return res[1:]


def getqueueforgame(game_id):  # gets the queue of a specific station game
    cur.execute(f'''SELECT
        og_id, house_id, queue
    FROM queue
    WHERE
        game_id = {game_id} AND (queue = 1 OR queue = 0)
    ORDER BY
        queue ASC,
        time ASC''')
    res = cur.fetchall()
    return res


def getplayingog(game_id):
    cur.execute(f'''
        SELECT
            og_id, house_id
        FROM queue
        WHERE 
            game_id = {game_id} AND queue = 0
    ''')
    res = cur.fetchone()
    return res


def getqueueforog(og_id, house_id):  # gets the stations queued by an og
    cur.execute(
        f'SELECT game_id, queue from queue WHERE og_id = {og_id} AND house_id = {house_id} ORDER BY queue ASC, time ASC')
    return cur.fetchall()


def getchatids():
    cur.execute(f'SELECT chat_id from member')
    res = cur.fetchall()
    return [i[0] for i in res]


def shorten(og_id: int, house_name: str):
    return f'{house_name[0]}{og_id}'


def gethouses():
    cur.execute(
        'SELECT og.id, house_id, house.name FROM og, house WHERE house_id = house.id ORDER BY house_id, og.id')
    return cur.fetchall()


def getgames():
    cur.execute('SELECT id, title FROM game ORDER BY id')
    return cur.fetchall()


def gethousename(house_id: int):
    cur.execute(f'SELECT name FROM house WHERE id = {house_id}')
    return cur.fetchone()[0]


def getgametitle(game_id: int):
    cur.execute(f'SELECT title FROM game WHERE id = {game_id}')
    return cur.fetchone()[0]


def getuser(user_id: int):
    cur.execute(f'''
        SELECT
            m.og_id, m.house_id, h.name, m.game_id, g.title, o.name
        FROM
            member m
        LEFT JOIN house h
            ON h.id = m.house_id
        LEFT JOIN game g
            ON g.id = m.game_id
        LEFT JOIN og o
            ON o.id = m.og_id AND o.house_id = m.house_id
        WHERE
            m.chat_id = {user_id}
    ''')
    res = cur.fetchone()
    return res if res else res


def getogqr(og_id, house_id, cat, id=None):
    table = 'quiz' if cat == 'q' else (
        'riddle' if cat == 'r' else ('game' if cat == 'g' else 'point'))
    cur.execute(
        f'SELECT * FROM {table}_og WHERE og_id = {og_id} AND house_id = {house_id}{f" AND {table}_id = {id}" if id else ""} ORDER BY {table}_id')
    res = cur.fetchone() if id else cur.fetchall()
    return res[3:] if id else [r[3:] for r in res]


def getogname(og_id, house_id):
    cur.execute(
        f"""SELECT house.name, og.name FROM og JOIN house ON (house.id = og.house_id) WHERE og.id = {og_id} AND house_id = {house_id}""")
    house_name, og_name = cur.fetchone()
    return og_name or f'{house_name} {og_id}'
