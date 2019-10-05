import os
from random import randint
from flask import Flask, request
import requests
import vk
from config import *
from threading import Thread
import json

session = vk.Session(access_token=VK_API_ACCESS_TOKEN)
api = vk.API(session, v=VK_API_VERSION)
app = Flask(__name__)

users = {}


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
                                              message='Привет, {}! Для входа введи код {} на странице https://geekclass.ru/activate.'.format(
                                                  users[user_id]['name'], users[user_id]['code']))
                        elif users[user_id]["state"] == "answering":
                            try:
                                number = int(update['object']['body'])
                                if number < 1 or number > 10:
                                    raise Exception("wrong number")

                                if 6 <= number <= 9:
                                    api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                                      message='Спасибо! Попрошу начислить тебе небольшой бонус.')

                                    requests.post(HOST + '/api/vk/stats',
                                                  {'id': users[user_id]['class_id'], "mark": number, "comment": ""})
                                    users[user_id]['state'] = "ready"
                                    save()
                                elif number == 10:
                                    api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                                      message='Вау! Видимо, сегодня занятие прошло особенно круто! Напиши пару слов, что именно тебе понравилось...')
                                    users[user_id]['state'] = "commenting"
                                    users[user_id]['temp_mark'] = number
                                    save()
                                else:
                                    api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                                      message='Хм! Кажется, все не очень весело... Расскажи, что тебе не понравилось, попробуем исправить...')
                                    users[user_id]['state'] = "commenting"
                                    users[user_id]['temp_mark'] = number
                                    save()
                            except:
                                api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                                  message='Нужно ввести число от 1 до 10.')
                        elif users[user_id]["state"] == "commenting":
                            try:
                                answer = update['object']['body']

                                api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                                  message='Спасибо! Попрошу начислить тебе небольшой бонус.')

                                answer = requests.post(HOST + '/api/vk/feedback', {'id': users[user_id]['class_id'],
                                                                                   "mark": users[user_id]['temp_mark'],
                                                                                   "comment": answer})

                                users[user_id]['state'] = "ready"
                                save()

                            except:
                                api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                                  message='Нужно ввести комментарий.')

                        else:
                            api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                              message='Лупа и Пупа пошли за зарплатой. Но новостей пока нет...')

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

                for old_user in users:
                    if users[old_user]['class_id'] == int(class_id):
                        del users[old_user]

                users[user_id]['state'] = 'ready'
                users[user_id]['class_id'] = int(class_id)
                users[user_id]['code'] = -1
                print("Sending ok")
                save()

                api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                  message='Активация прошла успешно.')

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


@app.route('/feedback', methods=['POST'])
def feedback():
    try:
        global users

        feedback_users = json.loads(request.form.get('users'))
        key = request.form.get('key')

        print(users)
        print(feedback_users)

        if key != KEY:
            return "error"

        for user_id in users:
            if users[user_id]['class_id'] in feedback_users:
                users[user_id]['state'] = "answering"
                api.messages.send(user_id=user_id, random_id=randint(-2147483648, 2147483647),
                                  message='Как прошли занятия сегодня? Оцени от 1 до 10, и я пришлю тебе небольшой бонус.'.format(
                                      message))

                save()

        return json.dumps({'state': 'ok'})

    except:
        return json.dumps({'state': 'error'})


Thread(target=bot).start()
app.run(host='0.0.0.0', port=9999, debug=False)
