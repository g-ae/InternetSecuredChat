import math
import random
import threading, time, re, socket, hashlib
import window_interaction
from signals import comm

stop_event = threading.Event()
connection: socket.socket = None  # type socket so that there are no errors in the rest of the code
connection_state = -1  # -1 not connected yet, 0 connection failed, 1 connected
last_own_sent_message = ""

server_messages = []


# ======================================================================================================================
#region ALL

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
    for i in range(0, len(text), 4):
        int_data.append(int.from_bytes(text[i:i + 4], "big"))
        try :
            result += text[i:i + 4].decode("utf-8")
        except :
            result += '*'

    if from_server: return int_data
    return result.replace("\x00", "")

#endregion
# ======================================================================================================================


# ======================================================================================================================
#region CONNECTION

def open_connection():
    global connection_state, connection
    connection_state = -1
    try:
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create new socket
        connection.connect((window_interaction.host, window_interaction.port))
    except (ConnectionRefusedError, socket.gaierror) as e:
        print("[CONNECTION] The connection couldn't be established.")
        connection_state = 0
        window_interaction.window.connected()
        exit(1)

    print("[CONNECTION] Open")
    connection_state = 1
    window_interaction.window.connected()

    try:
        stop_event.clear()
        t = threading.Thread(target=handle_message_reception)
        t.start()
    except KeyboardInterrupt:
        print("[CONNECTION] Stopped by Ctrl+C")
        close_connection()

def close_connection():
    global connection_state
    stop_event.set()
    if connection:  # Check if connection exists
        try:
            connection.shutdown(socket.SHUT_RDWR)
            connection.close()
        except:
            pass  # Socket might already be closed
    connection_state = -1
    print("[CONNECTION] Closed")

#endregion
# ======================================================================================================================


# ======================================================================================================================
#region MESSAGES

def handle_message_reception():
    try:
        while not stop_event.is_set():  # Tant qu'on ne demande pas d'arrêt
            try:
                firstdata = connection.recv(6)
                if firstdata == b'':
                    # NO DATA
                    continue

                message_type = firstdata[3]
                size = firstdata[-2:]

                # TODO : Test handling of image reception
                if message_type == ord('i'):
                    print("Received image request")
                    # 128 * 128 bytes or * 3 ?
                    connection.recv(size[0] * size[1])
                    continue

                data = connection.recv(int.from_bytes(size, "big") * 4)
            except (ConnectionAbortedError, OSError):
                exit(1)

            decoded_data = _decode_message(data)

            if data != b'':
                if message_type == ord('s'):
                    server_messages.append(data)
                    comm.chat_message.emit("<Server> " + decoded_data)
                else:
                    global last_own_sent_message
                    if not len(decoded_data) == 0 and decoded_data != last_own_sent_message:
                        last_own_sent_message = ""
                        comm.chat_message.emit("<User> " + decoded_data)
    except:
        pass

def send_message(text):
    global last_own_sent_message
    if text.startswith("/"):
        threading.Thread(target=server_task_command, args=[text[1:]]).start()
    elif not len(text) == 0:
        connection.send(_str_encode('t', text))
        comm.chat_message.emit("<You> " + text)
        last_own_sent_message = text

def send_server_message(text):
    comm.chat_message.emit("<You to Server> " + text)
    connection.send(_str_encode('s', text))

def send_server_message_no_encoding(bytes):
    comm.chat_message.emit("<You to Server> " + _decode_message(bytes))
    connection.send(b'ISCs' + int_encode(int(len(bytes) / 4), 2)  + bytes)

#endregion
# ======================================================================================================================


# ======================================================================================================================
#region TASKS

def server_task_command(text):
    # command example:
    # task shift encode 10
    # task hash verify

    command = text.split(' ')
    if command[0] != "task":
        show_error_message(f"Unknown command \"{command[0]}\"")
        return


    # Remove "task" from command
    del command[0]

    # Test there's another word than "task"
    if len(command) == 0:
        show_error_message("More arguments needed")
        return

    # command[1] gives "encode"/"decode" or "verify"/"hash"

    match (command[0]):
        case "shift" | "vigenere":
            if command[1] == "encode":
                shift_vigenere_encode(command[0], command)
            elif command[1] == "decode":
                shift_vigenere_decode(command[0], command)
        case "RSA":
            if command[1] == "encode":
                rsa_encode(command)
            elif command[1] == "decode":
                rsa_decode(command)
        case "hash":
            if command[1] == "verify":
                hash_command_verify(command)
            elif command[1] == "hash":
                hash_command_hash(command)
            else:
                show_error_message(f"Unknown command \"{command[1]}\"")
        case "DifHel":
            difhel(command)
            pass
        case _:
            show_error_message(f"Unknown task \"{command[0]}\"")

def show_error_message(error):
    comm.chat_message.emit(f"<Server> {error}")

def show_no_info_from_server():
    comm.chat_message.emit("<INFO> No info received from server, try again later.")

def test_input(text_array):
    """
    usage: ``if test_encode_input(text_array) == 0: return``
    :param text_array:
    :return: 1 if ok, 0 if not ok
    """
    if not text_array[-1].isnumeric():
        show_error_message("You must provide a number of words.")
        return 0
    if int(text_array[-1]) < 1 or int(text_array[-1]) > 10000:
        show_error_message("Number must be 1<x<10000.")
        return 0

    send_server_message(f"task {' '.join(text_array)}")
    return 1

#endregion
# ======================================================================================================================


# ======================================================================================================================
#region ENCODING

def wait_server_messages(number_of_messages, max_time = 2) -> bool:
    server_messages.clear()
    return wait_server_messages_no_empty(number_of_messages, max_time)

def wait_server_messages_no_empty(number_of_messages, max_time = 2) -> bool:
    """
    Waits for max "max_time" seconds for "number_of_messages" messages from server
    Server message list is not emptied !
    :param number_of_messages:
    :param max_time:
    :return: True if got all, False if max time exceeded
    """
    time_waited = 0
    while len(server_messages) != number_of_messages:
        time.sleep(0.1)
        time_waited += 0.1
        if time_waited >= max_time:
            show_no_info_from_server()
            return False
    return True

def difhel(text_array):
    server_messages.clear()
    send_server_message("task " + ' '.join(text_array))

    # Wait for 1 server message, if nothing received, return
    if not wait_server_messages(1):
        return

    # Generate prime number p and generator
    p = get_last_prime(random.randint(2, 4999))
    g = get_primitive_root(p)

    send_server_message(f"{p},{g}")

    # Wait for 1 server message, if nothing received, return
    if not wait_server_messages(1):
        return

    # Check if prime number and generator we sent is correct, if not, print error (shouldn't happen)
    if not _decode_message(server_messages[0]).__contains__("accepted"):
        print("Error, try again")
        server_messages.clear()
        return

    # P and G are correct
    # Wait for second server message (with their half-key)
    # Without emptying server_messages list because the message we need may already have been received
    if not wait_server_messages_no_empty(2):
        return

    server_half_key = int(_decode_message(server_messages[1]))
    my_secret_key = random.randint(1,5000)
    my_half_key = pow(g,my_secret_key,p) #g^a mod p

    send_server_message(str(my_half_key))

    # Wait for server message awaiting shared secret for validation
    if not wait_server_messages(1):
        return

    k = pow(server_half_key, my_secret_key, p) # B^a mod p

    send_server_message(str(k))
    server_messages.clear()

def shift_vigenere_encode(encryption_type: str, text_array: list[str]):

    """ shift_vigenere
        :param encryption_type: str: shift, vigenere
        :param text_array: list[str] - message
        This function encode the message and send them
    """

    if test_input(text_array) == 0: return

    if not wait_server_messages(2):
        return

    message = _decode_message(server_messages[0])
    key = message.split(' ')[-1]
    message_to_decode = _decode_message(server_messages[1], True)

    message_decoded = b''

    match encryption_type:
        case "vigenere":
            for i, c in enumerate(message_to_decode):
                intKey = int.from_bytes(key[i % len(key)].encode())
                message_decoded += int_encode(c + intKey, 4)

        case "shift":
            for i in message_to_decode:
                message_decoded += int_encode(i + int(key), 4)

    send_server_message_no_encoding(message_decoded)

    # Wait for reception of message confirming that everything is good
    wait_server_messages(1)

def rsa_encode(text_array):
    if test_input(text_array) == 0: return

    global server_messages

    if not wait_server_messages(2):
        return

    message = _decode_message(server_messages[0])
    x = re.findall("[0-9]+", message) # /\d+/ works as well but shows a warning on the console
    n = int(x[0])
    e = int(x[1])
    message_to_decode = _decode_message(server_messages[1], True)

    message_decoded = b''

    for c in message_to_decode:
        message_decoded += int_encode(pow(c, e, n), 4)
    send_server_message_no_encoding(message_decoded)

    # Wait for reception of message confirming that everything is good
    wait_server_messages(1)

#endregion
# ======================================================================================================================


# ======================================================================================================================
#region DECODING

def shift_vigenere_decode(type, text_array):
    print('shift_vigenere_decode')

def rsa_decode(text_array):
    if test_input(text_array) == 0: return

    global server_messages

    UPPER_LIMIT = 1000

    p = get_next_prime(random.randint(2, UPPER_LIMIT))
    q = get_next_prime(random.randint(2, UPPER_LIMIT))
    n = p * q
    k = (p - 1) * (q - 1)
    e = get_coprime(k)  # public key
    d = pow(e, -1, k)  # private key

    if not wait_server_messages(1):
        return

    send_server_message(f"{n},{e}")

    # Wait for server_message
    if not wait_server_messages(1):
        return

    # After receiving all needed messages
    message_to_decode = _decode_message(server_messages[0], True)

    message_decoded = b''

    for c in message_to_decode:
        message_decoded += int_encode(pow(c, d, n), 4)
    send_server_message_no_encoding(message_decoded)

    wait_server_messages(1)

#endregion
# ======================================================================================================================


# ======================================================================================================================
#region PRIME

def get_coprime(n) :
    while True:
        e = random.randint(2, n - 1)
        if math.gcd(e, n) == 1: return e

def is_prime(n: int) -> bool:
    if n <= 3:
        return n > 1
    if n % 2 == 0 or n % 3 == 0:
        return False
    limit = math.isqrt(n) + 1
    for i in range(5, limit, 6):
        if n % i == 0 or n % (i + 2) == 0:
            return False
    return True

def get_last_prime(num):
    curr_num = num - 1
    while curr_num > 3:
        if is_prime(curr_num):
            return curr_num
        curr_num -= 1
    return 3

def get_primitive_root(n):
    g = 1
    prime_factors = set(get_prime_factors(n - 1)) # pas de doublons
    ok = False
    while not ok:
        g += 1
        ok = True
        for pf in prime_factors:
            if pow(g,(n - 1) // pf,n) == 1:
                ok = False
    return g

def get_next_prime(n):
    num = n + 1
    while not is_prime(num):
        num += 1
    return num

def get_prime_factors(n) -> list[int]:
    curr_num = n
    curr_divisor = 2
    prime_factors = []
    while curr_num != 1:
        if curr_num % curr_divisor == 0:
            curr_num = int(curr_num / curr_divisor)
            prime_factors.append(curr_divisor)
        else:
            curr_divisor = get_next_prime(curr_divisor)
    return prime_factors

#endregion
# ======================================================================================================================


# ======================================================================================================================
#region HASHING

def hash_command_verify(command):
    send_server_message(f"task {' '.join(command)}")

    if not wait_server_messages(3):
        return

    message_to_hash = server_messages[1]
    hashed = server_messages[2]

    send_server_message(str(hashlib.sha256(message_to_hash) == hashed).lower())

    wait_server_messages(1)

def hash_command_hash(command):
    send_server_message(f"task {' '.join(command)}")

    if not wait_server_messages(2):
        return

    message_to_hash = server_messages[1]

    send_server_message(hashlib.sha256(_decode_message(message_to_hash).encode()).hexdigest())

    wait_server_messages(1)

#endregion
# ======================================================================================================================
