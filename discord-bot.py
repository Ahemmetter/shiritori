import discord
import random
import csv
import unidecode
import sqlite3
import os

# uses: https://github.com/datasets/world-cities

TOKEN = os.environ["ACCESS_TOKEN"]
solutions = ['name']
conn = sqlite3.connect("data.db")
db_length = 23019
channel_name = '📸│culture'
playable_letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
                    'u', 'v', 'w', 'x', 'y', 'z']  # which letters can still be played?
letter_dict = {'a': '🇦', 'b': '🇧', 'c': '🇨', 'd': '🇩', 'e': '🇪', 'f': '🇫', 'g': '🇬', 'h': '🇭', 'i': '🇮',
               'j': '🇯', 'k': '🇰', 'l': '🇱', 'm': '🇲', 'n': '🇳', 'o': '🇴', 'p': '🇵', 'q': '🇶', 'r': '🇷',
               's': '🇸', 't': '🇹', 'u': '🇺', 'v': '🇻', 'w': '🇼', 'x': '🇽', 'y': '🇾', 'z': '🇿'}

cursor = conn.cursor()

# open file for reading
with open('world-cities.csv') as world_cities_file:
    # read file as csv file
    csvReader = csv.reader(world_cities_file)
    # geoid : city, country, available?
    city_dict = {row[3]: [row[0], row[1], True] for row in csvReader}

# open file for reading
with open('slim-2.csv') as countrycodes_file:
    # read file as csv file
    csvReader = csv.reader(countrycodes_file)
    cc_dict = {row[0]: row[1] for row in csvReader}

client = discord.Client()


def leniency(text):
    clean_text = unidecode.unidecode(''.join([char for char in text if char.isalpha() or char.isspace()])).lower()
    return clean_text


def load_cities():
    for city in city_dict:
        if cc_dict[city_dict[city][1]]:
            cc = str(cc_dict[city_dict[city][1]]).lower()
            fl = str(leniency(str(city_dict[city][0]))[0]).lower()
            ll = str(leniency(str(city_dict[city][0]))[-1]).lower()
            cursor.execute(
                "INSERT INTO cities (geonameid, name, country, countrycode, firstletter, lastletter) VALUES (?, ?, ?, ?, ?, ?)",
                (int(city), str(city_dict[city][0]), str(city_dict[city][1]), cc, fl, ll))
    conn.commit()
    return


def check_answer(city_name, last_letter, user_id):
    print(city_name)
    print(last_letter)
    check_answer_cursor = conn.cursor()
    records = check_answer_cursor.execute(f"SELECT * FROM cities WHERE firstletter = ? AND solved IS NULL", (last_letter)).fetchall()
    for row in records:
        print(row)
        if leniency(row[1]) == leniency(city_name):
            check_answer_cursor.execute(f"UPDATE cities SET solved = ? WHERE geonameid = ?", (user_id, row[0]))
            conn.commit()
            update_lastletter(playable(row[5]))
            return row
    return []


def update_lastletter(last_letter):
    update_lastletter_cursor = conn.cursor()
    update_lastletter_cursor.execute(f"UPDATE letter SET lastletter = ?", (last_letter))
    conn.commit()
    return


def read_lastletter():
    read_lastletter_cursor = conn.cursor()
    last_letter = read_lastletter_cursor.execute("SELECT * FROM letter").fetchone()
    return str(last_letter[0])


def count_left():
    count_left_cursor = conn.cursor()
    count = count_left_cursor.execute("SELECT COUNT(solved) FROM cities").fetchone()[0]
    return count


def check_points(user_id):
    # function to check points for player
    check_points_cursor = conn.cursor()
    row = check_points_cursor.execute(f"SELECT * FROM scores WHERE discord_user = {user_id}").fetchone()
    if row:
        return row[1]
    else:
        return 0


def highscore():
    highscore_cursor = conn.cursor()
    row = highscore_cursor.execute(f"SELECT * FROM scores ORDER BY score DESC LIMIT 5").fetchall()
    return row


def initialize():
    initialize_cursor = conn.cursor()
    initialize_cursor.execute("DROP TABLE letter")
    initialize_cursor.execute("DROP TABLE cities")
    initialize_cursor.execute("DROP TABLE scores")
    conn.commit()

    initialize_cursor.execute("""CREATE TABLE letter (lastletter TEXT)""")
    initialize_cursor.execute(
        """CREATE TABLE cities (geonameid INTEGER, name TEXT, country TEXT, countrycode TEXT, firstletter TEXT, lastletter TEXT, solved INTEGER)""")
    initialize_cursor.execute("""CREATE TABLE scores (discord_user INTEGER, score INTEGER)""")
    conn.commit()

    initialize_cursor.execute("INSERT INTO letter VALUES('a')")
    conn.commit()

    load_cities()
    return


def give_points(user_id):
    # function to update points for player
    points = count_left()  # points added proportional to how many have already been answered
    give_points_cursor = conn.cursor()
    row = give_points_cursor.execute(f"SELECT * FROM scores WHERE discord_user = {user_id}").fetchone()
    if row:
        new_points = int(row[1]) + points
        give_points_cursor.execute(f"UPDATE scores SET score = {new_points} WHERE discord_user = {user_id}")
        conn.commit()
        return new_points

    else:
        # if not: make new entry
        give_points_cursor.execute(f"INSERT INTO scores VALUES ({user_id}, {points})")
        conn.commit()
        return points


def playable(last_letter):
    # check if the last letter is even available
    if last_letter not in playable_letters:
        # if it's not anymore in the list, find a random one right away (quick to search)
        last_letter = random.choice(playable_letters)
        print(f'No more cities available. Random next letter: {last_letter}')
        return last_letter
    else:
        # if it is in the list, check each city name
        playable_cursor = conn.cursor()
        count = playable_cursor.execute(f"SELECT COUNT(solved) FROM cities WHERE lastletter = ?", (last_letter)).fetchone()[0]
        print(count)
        if count == 0:
            playable_letters.remove(last_letter.lower())
            last_letter = random.choice(playable_letters)
            print(f'No more cities available. Random next letter: {last_letter}')
            return last_letter
        else:
            return last_letter


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    username = str(message.author).split('#')[0]
    user_message = str(message.content)
    channel = str(message.channel.name)
    print(f'{username}: {user_message} ({channel})')
    msg_user_id = message.author.id
    last_letter = read_lastletter()

    if message.author == client.user:
        return

    if message.channel.name == channel_name:

        if user_message.lower() == '&points':
            await message.channel.send(f'You have {check_points(msg_user_id)} points.')
            return

        elif user_message.lower() == '&letter':
            await message.channel.send(f'Next letter: **{last_letter.upper()}**')
            return

        elif user_message.lower() == '&left':
            count = count_left()
            await message.channel.send(f'There are **{db_length - count}** cities left.')
            return

        elif user_message.lower() == '&found':
            count = count_left()
            percentage = round(count / db_length, 2)

            await message.channel.send(f'You\'ve found **{count}** cities ({percentage}%).')
            return

        elif user_message.lower() == '&help':
            await message.channel.send(f'Available commands: points, left, found, hs, letter')
            return

        elif (user_message.lower() == '&initialize') and message.author.guild_permissions.manage_guild:
            initialize()
            await message.channel.send(f'Initialized. Everything is back to 0')
            return

        elif user_message.lower() == '&hs':
            row = highscore()
            print(row)
            for entry in row:
                user = await client.fetch_user(int(entry[0]))
                await message.channel.send(f'{user}: {entry[1]} points')
            return

        else:
            answer_row = check_answer(user_message, last_letter, msg_user_id)
            if answer_row:
                msgbot = await message.channel.send(f'{answer_row[1]}, {answer_row[2]} :flag_{answer_row[3]}:')
                give_points(msg_user_id)
                await msgbot.add_reaction(f"{letter_dict[read_lastletter()]}")
                return

            else:
                pass

    if user_message.lower() == '&where':
        await message.channel.send(f'You can play in the channel `{channel_name}`')
        return

    #elif (user_message.lower() == '&channel') and message.author.guild_permissions.manage_guild:
     #   initialize()
      #  await message.channel.send(f'Initialized. Everything is back to 0')
       # return


client.run(TOKEN)
