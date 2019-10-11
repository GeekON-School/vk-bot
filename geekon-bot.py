import os
from random import randint, choice
from flask import Flask, request
import requests
import vk
from config import *
from threading import Thread
import json
from datetime import datetime

session = vk.Session(access_token=VK_API_ACCESS_TOKEN)
api = vk.API(session, v=VK_API_VERSION)
app = Flask(__name__)

users = {}

jokes = [
    '😼 Лупа и Пупа пошли за зарплатой. Но новостей пока нет...',
    '😼 Ну и запросы у вас! - сказал бот для ВК и завис...',
    '😼 Позовите Ростислава! - Ростислав в архиве! - Так разорхивируйте его...',
    '🦄🦄🦄',
    '🤔 Хм, если тебе нечем заняться, можно доработать меня на http://github.com/geekon-school/vk-bot.',
    'https://storage.geekclass.ru/images/1ffc5723-0f4d-419e-bc8e-b82ad008abd4.png',
    '🙈 Нужно было ставить линукс...',
    '🐷',
    '🤹'
]


def save():
    global users
    with open('data.json', 'w') as f:
        json.dump(users, f)


def load():
    global users
    try:
        with open('data.json', 'r') as f:
            users = json.load(f)
        save()
    except:
        save()


load()


def generate():
    global users

    while True:
        number = randint(1111, 9999)

        found = False
        for user in users.values():
            if user['code'] == number:
                found = True

        if not found:
            break
    return number


def bot():
    global users
    global api

    print("hey!")

    # Первый запрос к LongPoll: получаем server и key
    longPoll = api.groups.getLongPollServer(group_id=GROUP_ID)
    server, key, ts = longPoll['server'], longPoll['key'], longPoll['ts']
    while True:
        try:
            # Последующие запросы: меняется только ts
            longPoll = requests.post('%s' % server, data={'act': 'a_check',
                                                          'key': key,
                                                          'ts': ts,
                                                          'wait': 25}).json()

            if longPoll['updates'] and len(longPoll['updates']) != 0:
                for update in longPoll['updates']:
                    if update['type'] == 'message_new':
                        print(update)

                        user_id = str(update['object']['user_id'])

                        # Помечаем сообщение от этого пользователя как прочитанное
                        api.messages.markAsRead(peer_id=update['object']['user_id'])

                        if user_id not in users:
                            users[user_id] = {
                                "name": api.users.get(user_ids=user_id)[0]['first_name'],
                                "state": "activating",
                                "code": generate(),
                                "class_id": -1
                            }
                            save()
                        if users[user_id]["state"] == "activating":
                            api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                              message='👋 ‍Привет, {}! Если ты уже учишься у нас, нужно связать твой аккаунт с GeekClass, для этого введи код {} на странице:\n\n https://geekclass.ru/activate \n\nЕсли вы хотите задать вопрос о нашей школе, напишите сообщение Ростиславу Бородину (vk.com/roctbb).'.format(
                                                  users[user_id]['name'], users[user_id]['code']))
                        elif users[user_id]["state"] == "answering":
                            try:
                                number = int(update['object']['body'])
                                if number < 1 or number > 10:
                                    raise Exception("wrong number")

                                if 6 <= number <= 9:
                                    api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                                      message='👍👍👍 Спасибо! Попрошу начислить тебе небольшой бонус.')

                                    result = requests.post(HOST + '/api/vk/feedback',
                                                           {'id': users[user_id]['class_id'], "mark": number,
                                                            "comment": "", "key": KEY})
                                    print(result.text)
                                    users[user_id]['state'] = "ready"
                                    save()
                                elif number == 10:
                                    api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                                      message='😎 Вау! Видимо, сегодня занятие прошло особенно круто! Напиши пару слов, что именно тебе понравилось...')
                                    users[user_id]['state'] = "commenting"
                                    users[user_id]['temp_mark'] = number
                                    save()
                                else:
                                    api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                                      message='😯 Хм! Кажется, все не очень весело... Расскажи, что тебе не понравилось, попробуем исправить...')
                                    users[user_id]['state'] = "commenting"
                                    users[user_id]['temp_mark'] = number
                                    save()
                            except:
                                api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                                  message='✋ Нужно ввести число от 1 до 10.')
                        elif users[user_id]["state"] == "commenting":
                            try:
                                answer = update['object']['body']

                                api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                                  message='👍👍👍 Спасибо! Попрошу начислить тебе небольшой бонус.')

                                requests.post(HOST + '/api/vk/feedback', {'id': users[user_id]['class_id'],
                                                                          "mark": users[user_id]['temp_mark'],
                                                                          "comment": answer, "key": KEY})
                                users[user_id]['state'] = "ready"
                                save()

                            except:
                                api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                                  message='✋ Нужно ввести комментарий.')

                        elif users[user_id]["state"] == "ready":
                            if datetime.now().hour <= 4 or  datetime.now().hour >= 21:
                                api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                                  message="🛌💤💤💤")
                            else:
                                api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                              message=choice(jokes))

            # Меняем ts для следующего запроса
            ts = longPoll['ts']
        except:
            longPoll = api.groups.getLongPollServer(group_id=GROUP_ID)
            server, key, ts = longPoll['server'], longPoll['key'], longPoll['ts']


@app.route('/', methods=['GET'])
def index():
    return "Waiting for the thunder!"


@app.route('/activate', methods=['POST'])
def activate():
    try:
        global users

        code = request.form.get('code')
        class_id = request.form.get('class_id')
        key = request.form.get('key')

        if key != KEY:
            raise Exception("wrong key")

        if int(code) < 1111:
            return json.dumps({'state': 'error'})

        for user_id in users:
            if users[user_id]['code'] == int(code):
                dublicate = False
                for old_user in users:
                    if users[old_user]['class_id'] == int(class_id):
                        del users[old_user]

                users[user_id]['state'] = 'ready'
                users[user_id]['class_id'] = int(class_id)
                users[user_id]['code'] = -1
                print("Sending ok")
                save()

                api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                  message='👍👍👍 Активация прошла успешно.')

                api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                  message='Теперь я смогу присылать тебе важные новости и давать задания (конечно, за геккоины)!')

                return json.dumps({'state': 'ok', 'user_id': user_id})

        raise Exception("no code")
    except:
        return json.dumps({'state': 'error'})


@app.route('/message', methods=['POST'])
def message():
    try:
        global users

        message = request.form.get('message')
        key = request.form.get('key')

        if key != KEY:
            return "error"

        for user_id in users:
            api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                              message='{}'.format(message))

        return json.dumps({'state': 'ok'})

    except:
        return json.dumps({'state': 'error'})


@app.route('/notify', methods=['POST'])
def notify():
    try:
        global users

        message = request.form.get('message')
        key = request.form.get('key')
        class_id = str(request.form.get('class_id'))

        if key != KEY:
            return "{'state': 'error'}"

        for user_id in users:
            try:
                if str(users[user_id]['class_id']) == class_id:
                    api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647), message='{}'.format(message))
            except Exception as e:
                print(e)

        return json.dumps({'state': 'ok'})

    except Exception as e:
        print(e)
        return json.dumps({'state': 'error'})


@app.route('/feedback', methods=['POST'])
def feedback():
    try:
        global users

        feedback_users = json.loads(request.form.get('users'))
        key = request.form.get('key')

        print(feedback_users)

        if key != KEY:
            return "error"
        row = [{
            "action": {
                "type": "text",
                "payload": f"{i}",
                "label": f"{i}"
            },
            "color": "negative"
        } for i in range(1, 6)]

        row += [{
            "action": {
                "type": "text",
                "payload": f"{i}",
                "label": f"{i}"
            },
            "color": "primary"
        } for i in range(6, 10)]
        row += [{
            "action": {
                "type": "text",
                "payload": "10",
                "label": "10"
            },
            "color": "positive"
        }]

        keyboard = {
            "one_time": True,
            "buttons": [row[:4], row[4:8], row[8:]]
        }

        for user_id in users:
            if users[user_id]['class_id'] in feedback_users:
                users[user_id]['state'] = "answering"
                result = api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                           message='👀 Как прошли занятия сегодня? Оцени от 1 до 10, и я пришлю тебе небольшой бонус.'.format(
                                               message), keyboard=json.dumps(keyboard))

                save()

        return json.dumps({'state': 'ok'})

    except Exception as e:
        print(e)
        return json.dumps({'state': 'error'})


Thread(target=bot).start()
app.run(host='0.0.0.0', port=9999, debug=False)
