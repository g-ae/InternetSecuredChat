import threading, time, re, socket
import window_interaction

HOST = 'vlbelintrocrypto.hevs.ch'
PORT = 6000
connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection_state = -1  # -1 not connected yet, 0 connection failed, 1 connected
last_own_sent_message = ""

server_messages = []

# ==========================================================
#                           ALL
# ==========================================================


def single_char_encode(chr):
    encoded = chr.encode('utf-8')
    return (4 - len(encoded)) * b'\x00' + encoded

def int_encode(int, bytenum):
    return int.to_bytes(bytenum, byteorder='big')

def _str_encode(type, string):
    # ISC Header + type of message + string length encoded in big-endian
    msg = b'ISC' + type.encode('utf-8') + int_encode(len(string), 2)

    # Encode char as unicode (up to 4 chars) -> if is only one, 3 times \x00 then 1 time ascii of char \x97
    for s in string:
        msg += single_char_encode(s)

    return msg

def _decode_message(text, from_server = False):
    result = ''
    int_data = []
    for i in range(6, len(text), 4):
        int_data.append(int.from_bytes(text[i:i + 4], "big"))
        try :
            result += text[i:i + 4].decode("utf-8")
        except :
            result += '*'

    if from_server: return int_data
    return result.replace("\x00", "")

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

# ==========================================================
#                           MESSAGES
# ==========================================================

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

def send_server_message_no_encoding(bytes):
    window_interaction.add_message("<You to Server> " + _decode_message(bytes))
    connection.send(bytes)


# ==========================================================
#                       SERVER COMMAND
# ==========================================================

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
                shift_vigenere_encode("shift",split_text)
            elif type_code == "decode":
                pass
        case "vigenere":
            if type_code == "encode":
                shift_vigenere_encode("vigenere", split_text)
            elif type_code == "decode":
                pass
        case "RSA":
            if type_code == "encode":
                rsa_encode(split_text)

        case _:
            window_interaction.add_message("<Server> Error: Unknown task")

def server_command_hash(text_array):
    match text_array[0]:
        case "verify":
            pass
        case "hash":
            pass


# ==========================================================
#                         ENCODING
# ==========================================================

def test_encode_input(text_array):
    """
    usage: ``if test_encode_input(text_array) == 0: return``
    :param text_array:
    :return: 1 if ok, 0 if not ok
    """
    if not text_array[-1].isnumeric():
        window_interaction.add_message("<Server> You must provide a number of words for encoding.")
        return 0
    if int(text_array[-1]) < 1 or int(text_array[-1]) > 10000:
        window_interaction.add_message("<Server> Encoding number must be 1<x<10000.")
        return 0

    send_server_message(f"task {' '.join(text_array)}")
    return 1

# type == shift, vigenere
def shift_vigenere_encode(type, text_array):
    if test_encode_input(text_array) == 0: return

    global server_messages

    key = ''
    message_to_decode = ''
    time_waited = 0

    while True:
        time.sleep(0.5)
        time_waited += 0.5
        if len(server_messages) == 2:
            message = _decode_message(server_messages[0])
            key = message.split(' ')[-1]
            message_to_decode = _decode_message(server_messages[1], True)
            break
        if time_waited == 2:
            window_interaction.add_message("<INFO> No info received from server, try again later.")
            return

    message_decoded = b''

    match type:
        case "vigenere":
            for i, c in enumerate(message_to_decode):
                intKey = int.from_bytes(key[i % len(key)].encode())
                message_decoded += int_encode(c + intKey, 4)

        case "shift":
            for i in message_to_decode:
                message_decoded += int_encode(i + int(key), 4)

    send_server_message_no_encoding(b'ISCs' + int_encode(len(message_to_decode), 2) + message_decoded)

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

def rsa_encode(text_array):
    if test_encode_input(text_array) == 0: return

    global server_messages

    message_to_decode = ''
    time_waited = 0
    n = 0
    e = 0

    while True:
        time.sleep(0.5)
        time_waited += 0.5
        if len(server_messages) == 2:
            message = _decode_message(server_messages[0])
            x = re.findall("[0-9]+",message) # /\d+/ works as well but shows a warning on the console
            n = int(x[0])
            e = int(x[1])

            message_to_decode = _decode_message(server_messages[1])
            break
        if time_waited == 2:
            window_interaction.add_message("<INFO> No info received from server, try again later.")
            return

    msg_bytes = b''

    for c in message_to_decode:
        msg_bytes += int_encode(rsa_encode_char(ord(c), e, n), 4)

    send_server_message_no_encoding(b'ISCs' + int_encode(len(message_to_decode), 2) + msg_bytes)

def rsa_encode_char(char_ascii, e, n):
    val = char_ascii
    for i in range(e):
        val *= char_ascii
        val = val % n
    print(val)
    return val