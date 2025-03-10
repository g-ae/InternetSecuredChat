import socket
import threading
import window_interaction
import time

HOST = 'vlbelintrocrypto.hevs.ch'
PORT = 6000
connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection_state = -1  # -1 not connected yet, 0 connection failed, 1 connected
last_own_sent_message = ""

server_messages = []


# ALL

def _str_encode(type, string):
    # ISC Header + type of message + string length encoded in big-endian
    msg = b'ISC' + type.encode('utf-8') + len(string).to_bytes(2, byteorder='big')

    # Encode char as unicode (up to 4 chars) -> if is only one, 3 times \x00 then 1 time ascii of char \x97
    for s in string:
        encoded = s.encode('utf-8')
        msg += (4 - len(encoded)) * b'\x00' + encoded

    return msg


def _decode_message(text):
    try:
        return text.decode("utf-8")[6:].replace("\x00", "")
    except UnicodeDecodeError:
        print(f"[DECODING]  Received text couldn't be decoded -> {text}")
        return ""


def open_connection():
    global connection_state
    global connection
    try:
        connection.connect((HOST, PORT))
    except (ConnectionRefusedError, socket.gaierror) as e:
        print("[CONNECTION] The connection couldn't be established.")
        print(e)
        connection_state = 0
        exit(1)

    print("[CONNECTION] Open")
    connection_state = 1
    try:
        t = threading.Thread(target=handle_message_reception)
        t.start()
    except KeyboardInterrupt:
        print("[CONNECTION] Stopped by Ctrl+C")
        connection.close()


def close_connection():
    connection.close()
    print("[CONNECTION] Closed")


# MESSAGES

def handle_message_reception():
    while True:
        try:
            data = connection.recv(65536)
        except ConnectionAbortedError:
            exit(1)

        decoded_data = _decode_message(data)
        if data != b'':
            if chr(data[3]) == 's':
                server_messages.append(data)
                window_interaction.add_message("<Server> " + decoded_data)
            else:
                global last_own_sent_message
                if not len(decoded_data) == 0 and decoded_data != last_own_sent_message:
                    last_own_sent_message = ""
                    window_interaction.add_message("<User> " + decoded_data)


def send_message(text):
    global last_own_sent_message
    if text.startswith("/"):
        threading.Thread(target=server_command, args=[text[1:]]).start()
    elif not len(text) == 0 and text != last_own_sent_message:
        connection.send(_str_encode('t', text))
        window_interaction.add_message("<You> " + text)
        last_own_sent_message = text


def send_server_message(text):
    window_interaction.add_message("<You to Server> " + text)
    connection.send(_str_encode('s', text))


# SERVER COMMAND

def server_command(text):
    match text.split(' ')[0]:
        case "task":
            server_command_task(text.split(' ')[1:])
        case "hash":
            server_command_hash(text.split(' ')[1:])


def server_command_task(text_array):
    """

    :param text: whole text with or without "task" -> splitted by " ", ex : ['shift', 'encode', '2000']
    :return:
    """

    split_text = text_array
    if split_text[0] == "task":
        del split_text[0]

    # gives "encode" or "decode"
    type_code = split_text[1]

    match (split_text[0]):
        case "shift":
            if type_code == "encode":
                shift_encode(split_text)
            elif type_code == "decode":
                pass
        case "vigenere":
            if type_code == "encode":
                vigenere_encode(split_text)
            elif type_code == "decode":
                pass
        case "RSA":
            pass
        case _:
            pass


def server_command_hash(text_array):
    match text_array[0]:
        case "verify":
            pass
        case "hash":
            pass


# ENCODING

def shift_encode(text_array):
    if not text_array[-1].isnumeric():
        window_interaction.add_message("<Server> You must provide a number of words for encoding.")
        return
    if int(text_array[-1]) < 1 or int(text_array[-1]) > 10000:
        window_interaction.add_message("<Server> Encoding number must be 1<x<10000.")
        return

    send_server_message(f"task {' '.join(text_array)}")
    global server_messages
    message_to_decode = ''
    key = ''

    time_waited = 0
    while True:
        time.sleep(0.5)
        time_waited += 0.5
        if len(server_messages) == 2:
            message = _decode_message(server_messages[0])
            key = message.split(' ')[-1]
            message_to_decode = _decode_message(server_messages[1])
            break
        if time_waited == 2:
            window_interaction.add_message("<INFO> No info received from server, try again later.")
            return

    message_decoded = ''
    for i in message_to_decode:
        message_decoded += chr(ord(i) + int(key))

    send_server_message(message_decoded)
    server_messages = []

    time_waited = 0
    while True:
        time.sleep(0.5)
        time_waited += 0.5
        if len(server_messages) != 0:
            server_messages = server_messages[1:]
            break

        if time_waited == 2:
            window_interaction.add_message("<INFO> No info received from server, try again later.")
            return


def vigenere_encode(text_array):
    if not text_array[-1].isnumeric():
        window_interaction.add_message("<Server> You must provide a number of words for encoding.")
        return
    if int(text_array[-1]) < 1 or int(text_array[-1]) > 10000:
        window_interaction.add_message("<Server> Encoding number must be 1<x<10000.")
        return

    send_server_message(f"task {' '.join(text_array)}")
    global server_messages
    message_to_decode = ''
    key = ''


    time_waited = 0
    while True:
        time.sleep(0.5)
        time_waited += 0.5
        if len(server_messages) == 2:
            message = _decode_message(server_messages[0])
            key = message.split(' ')[-1]
            message_to_decode = _decode_message(server_messages[1])
            break
        if time_waited == 2:
            window_interaction.add_message("<INFO> No info received from server, try again later.")
            return

    message_decoded = ''
    full_key = ''
    index = 0
    for i in range(len(message_to_decode)):
        if index == len(key): index = 0
        full_key += key[index]
        index += 1

    for i in range(len(message_to_decode)):
        char = message_to_decode[i]
        shift = int(abs(ord(char) - ord(full_key[i])))
        char_encrypted = chr(ord(char) + shift)
        message_decoded += char_encrypted

    send_server_message(message_decoded)
    server_messages = []

    time_waited = 0
    while True:
        time.sleep(0.5)
        time_waited += 0.5
        if len(server_messages) != 0:
            server_messages = server_messages[1:]
            break

        if time_waited == 2:
            window_interaction.add_message("<INFO> No info received from server, try again later.")
            return