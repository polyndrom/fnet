import random
from datetime import datetime
import hashlib

from flask import request, Blueprint
from pymemcache.client import base

from validator import validate, validate_token, FieldValidator, ValidationError
from message_manager import MessageManager
from response_manager import ResponseManager
import config.config as config
from database import database_cursor

messages = Blueprint('messages', __name__)


@messages.route('/', methods=['POST'])
def send_message():
    validators = [
        FieldValidator('receiver_id').required(),
        FieldValidator('token').required(),
        FieldValidator('text').required().max_len(config.max_message_text_len)
    ]
    receiver_id, token, text = validate(request.get_json(), validators)
    sender_id = validate_token(token)
    database_cursor.execute('INSERT INTO "Message"(sender_id, receiver_id, text) '
                            'VALUES (%s, %s, %s)', (sender_id, receiver_id, text,))
    return ResponseManager.success()


@messages.route('/dialogs', methods=['GET'])
def get_dialogs():
    validators = [
        FieldValidator('token').required()
    ]
    token = validate(request.args, validators)
    user_id = validate_token(token)
    database_cursor.execute('SELECT sender_id, receiver_id, text, time FROM "Message" '
                            'WHERE (sender_id = %s OR receiver_id = %s) ORDER BY time DESC', (user_id, user_id,))
    messages_data = database_cursor.fetchall()
    dialogs = {}
    for message in messages_data:
        sender_id, receiver_id, text, time = message.values()
        dialog_data = {'companion_name': '{} {}', 'text': text, 'time': time, 'sender_id': sender_id}
        if user_id == sender_id and receiver_id not in dialogs.keys():
            database_cursor.execute('SELECT first_name, last_name FROM "User" WHERE id = %s', (receiver_id,))
            companion_data = database_cursor.fetchone()
            dialog_data['companion_name'] = dialog_data['companion_name'].format(companion_data.get('first_name'), companion_data.get('last_name'))
            dialogs[receiver_id] = dialog_data
        if user_id == receiver_id and sender_id not in dialogs.keys():
            database_cursor.execute('SELECT first_name, last_name FROM "User" WHERE id = %s', (sender_id,))
            companion_data = database_cursor.fetchone()
            dialog_data['companion_name'] = dialog_data['companion_name'].format(companion_data.get('first_name'), companion_data.get('last_name'))
            dialogs[sender_id] = dialog_data
    return ResponseManager.success({'dialogs': dialogs})


@messages.route('/<int:second_member_id>', methods=['GET'])
def get_messages(second_member_id):
    validators = [
        FieldValidator('token').required(),
    ]
    token = validate(request.args, validators)
    first_member_id = validate_token(token)
    database_cursor.execute('SELECT sender_id, text, time FROM "Message" WHERE '
                            '(sender_id = %s AND receiver_id = %s) OR (receiver_id = %s AND sender_id = %s)',
                            (first_member_id, second_member_id, first_member_id, second_member_id))
    messages_data = database_cursor.fetchall()
    result = []
    for message_data in messages_data:
        sender_id, text, time = tuple(message_data.values())
        result.append({'sender_id': sender_id, 'text': text, 'time': time})
    return ResponseManager.success({'messages': result})

