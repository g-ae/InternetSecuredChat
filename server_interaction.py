import socket
import threading
import window_interaction

HOST = 'vlbelintrocrypto.hevs.ch'
PORT = 6000
connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection_state = -1   # -1 not connected yet, 0 connection failed, 1 connected
last_own_sent_message = ""

# ALL

def _str_encode(type, string):
    # ISC Header + type of message + string length encoded in big-endian
    msg = b'ISC' + type.encode('utf-8') + len(string).to_bytes(2, byteorder='big')

    # Encode char as unicode (up to 4 chars) -> if is only one, 3 times \x00 then 1 time ascii of char \x97
    for s in string:
        encoded = s.encode('utf-8')
        msg += (4-len(encoded))*b'\x00' + encoded

    return msg

def _decode_message(text):
    return text.decode()[6:].replace("\x00", "")

def open_connection():
    global connection_state
    global connection
    try:
        connection.connect((HOST, PORT))
    except (ConnectionRefusedError, socket.gaierror) as e:
        print("[ServerInteraction] The connection couldn't be established.")
        print(e)
        connection_state = 0
        exit(1)

    print("Connection open")
    connection_state = 1
    try:
        t = threading.Thread(target=handle_message_reception)
        t.start()
    except KeyboardInterrupt:
        print("Stopped by Ctrl+C")
        connection.close()

def close_connection():
    connection.close()
    print("Connection closed")

# MESSAGES

def handle_message_reception():
    while True:
        try:
            data = connection.recv(65536)
        except ConnectionAbortedError:
            exit(1)
        decoded_data = _decode_message(data)
        global last_own_sent_message
        if not len(decoded_data) == 0 and decoded_data != last_own_sent_message:
            last_own_sent_message = ""
            window_interaction.add_message("<User> " + _decode_message(data))

def send_message(text):
    global last_own_sent_message
    if not len(text) == 0 and text != last_own_sent_message:
        connection.send(_str_encode('t', text))
        window_interaction.add_message("<You> " + text)
        last_own_sent_message = text

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
            pass
        case "vigenere":
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