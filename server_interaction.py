import math
import random
import threading, time, re, socket, hashlib
import window_interaction
from signals import comm

# region Variables

stop_event = threading.Event()      # Event to signal thread termination
connection: socket.socket = None    # Socket connection to server
connection_state = -1               # Connection states: -1 (not connected), 0 (failed), 1 (connected)
last_own_sent_message = ""          # Store last message to prevent duplicates
server_messages = []                # Store messages received from server
saved_message = []                  # Archive received messages for later use

# endregion

# region Message Encoding/Decoding Utils

def single_char_encode(chr):
    """
    Encode a single character to UTF-8 with padding.

    Args:
        chr (str): Single character to encode

    Returns:
        bytes: Encoded character with padding to 4 bytes
    """

    encoded = chr.encode('utf-8')
    return (4 - len(encoded)) * b'\x00' + encoded

def int_encode(int, bytenum):
    """
    Encode an integer to bytes with specified length.

    Args:
        int (int): Integer to encode
        bytenum (int): Number of bytes to use

    Returns:
        bytes: Encoded integer in big-endian format
    """

    return int.to_bytes(bytenum, byteorder='big')

def _str_encode(type, string):
    """
    Encode a string message using the ISC protocol format.

    Args:
        type (str): Message type identifier
        string (str): Message content to encode

    Returns:
        bytes: Complete encoded message
    """

    # ISC Header + type of message + string length encoded in big-endian
    msg = b'ISC' + type.encode('utf-8') + int_encode(len(string), 2)

    # Encode each character as unicode (up to 4 bytes per char)
    for s in string:
        msg += single_char_encode(s)

    return msg

def _decode_message(text, from_server=False):
    """
    Decode a message from bytes to string/integers.

    Args:
        text (bytes): Encoded message
        from_server (bool, optional): If True, return integer values instead of string. Defaults to False.

    Returns:
        str/list: Decoded string or list of integer values
    """

    result = ''
    int_data = []
    for i in range(0, len(text), 4):
        int_data.append(int.from_bytes(text[i:i + 4], "big"))
        try:
            result += text[i:i + 4].decode("utf-8")
        except:
            result += '*'

    if from_server: return int_data
    return result.replace("\x00", "")

# endregion

# region Connection Handling

def open_connection():
    """
    Establish a connection to the server.
    Updates global connection state and starts message reception thread.
    """

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
    """
    Close the connection to the server.
    Signals the message reception thread to stop and closes the socket.
    """

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

# endregion

# region Messages Handling

def handle_message_reception():
    """
    Background thread function to continuously receive and process messages from server.
    Runs until stop_event is set.
    """
    try:
        while not stop_event.is_set():  # Continue until stop is requested
            try:
                firstdata = connection.recv(6)
                if firstdata == b'':
                    # No data received
                    continue

                message_type = firstdata[3]
                size = firstdata[-2:]

                # Handle image data (not fully implemented)
                if message_type == ord('i'):
                    print("Received image request")
                    # Read image data (128x128x3 bytes)
                    connection.recv(size[0] * size[1] * 3)
                    continue

                data = connection.recv(int.from_bytes(size, "big") * 4)
                saved_message.append(data)
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
    """
    Send a message to the server.
    Handles special commands prefixed with '/' or sends as regular message.

    Args:
        text (str): Message text to send
    """
    global last_own_sent_message
    if text.startswith("/"):
        match text:
            case x if x.startswith("/task"):
                threading.Thread(target=server_task_command, args=[text[1:]]).start()
            case x if x.startswith("/crypt"):
                send_crypted_server_message(text[1:])
            case x if x.startswith("/decrypt"):
                show_decrypted_server_message(text[1:])
            case x if x.startswith("/clear"):
                window_interaction.window._clear_chat()
            case _:
                show_error_message(f"Unknown command \"{text.split(' ')[0]}\"")
                return
    elif not len(text) == 0:
        connection.send(_str_encode('t', text))
        comm.chat_message.emit("<You> " + text)
        last_own_sent_message = text

def send_server_message(text):
    """
    Send a message directly to the server.

    Args:
        text (str): Message text to send to server
    """
    comm.chat_message.emit("<You to Server> " + text)
    connection.send(_str_encode('s', text))

def send_crypted_server_message(text):
    """
    Encrypt and send a message to the server.

    Args:
        text (str): Command and message to encrypt
    """
    command = text.split(' ')
    del command[0]  # Remove "crypt" from command

    # Check for additional arguments
    if len(command) == 0:
        show_error_message("More arguments needed")
        return

    type = window_interaction.window._get_encoding_values()[0]

    try:
        msg = b''
        for s in command[0]: msg += single_char_encode(s)

        message_crypted = b''
        message_to_crypt = _decode_message(msg, True)
        key = command[1]

        match type:
            case "shift":
                for i in message_to_crypt:
                    message_crypted += int_encode(i + int(key), 4)
            case "vigenere":
                for i, c in enumerate(message_to_crypt):
                    intKey = int.from_bytes(key[i % len(key)].encode())
                    message_crypted += int_encode(c + intKey, 4)
            case "RSA":
                n = int(command[1])
                e = int(command[2])
                for c in message_to_crypt:
                    message_crypted += int_encode(pow(c, e, n), 4)
            case _:
                show_error_message(f"{type} is not a valid encoding")

        send_message(_decode_message(message_crypted))

    except:
        show_error_message(f"Invalid arguments, try again")

def show_decrypted_server_message(text):
    """
    Decrypt and display a previously received message.

    Args:
        text (str): Command with index of message to decrypt and key
    """
def show_decrypted_server_message(text) :
    def missing_args(encoding):
        error_msg = f"Usage ({encoding}) /decrypt "
        if encoding == "shift" or encoding == "vigenere":
            error_msg += "<message_index>"
        elif encoding == "RSA":
            error_msg += "<n> <e>"
        else:
            error_msg = f"{encoding} can't be used for decryption."

        show_error_message(error_msg)
        return

    command = text.split(' ')
    del command[0]  # Remove "decrypt" from command

    # Get chosen encoding
    encoding = window_interaction.window._get_encoding_values()[0]

    # Check for additional arguments
    if len(command) < 2:
        missing_args(encoding)
        return

    try:
        message_decrypted = b''
        message_num = int(command[0])
        message_to_decrypt = _decode_message(saved_message[-message_num], True)
        key = command[1]

        match encoding:
            case "shift":
                for i in message_to_decrypt:
                    message_decrypted += int_encode(i - int(key), 4)
            case "vigenere":
                for i, c in enumerate(message_to_decrypt):
                    intKey = int.from_bytes(key[i % len(key)].encode())
                    message_decrypted += int_encode(c - intKey, 4)
            case "RSA":
                if len(command) < 3:
                    missing_args(encoding)
                    return

                n = int(command[1])
                d = int(command[2])
                for c in message_to_decrypt:
                    message_decrypted += int_encode(pow(c, d, n), 4)
            case _:
                show_error_message(f"{encoding} can't be used for decryption.")

        comm.decoded_message.emit(_decode_message(message_decrypted))

    except:
        show_error_message(f"Invalid arguments, try again")

def send_server_message_no_encoding(bytes):
    """
    Send raw bytes to the server without encoding.
    For use with pre-encoded messages.

    Args:
        bytes (bytes): Pre-encoded message data
    """
    comm.chat_message.emit("<You to Server> " + _decode_message(bytes))
    connection.send(b'ISCs' + int_encode(int(len(bytes) / 4), 2) + bytes)

# endregion

# region Tasks Handling

def server_task_command(text):
    """
    Process task commands for cryptographic operations.
    Parses the command and delegates to appropriate handler functions.

    Args:
        text (str): Task command string (e.g., "task shift encode 10")
    """
    # Parse the command
    command = text.split(' ')
    del command[0]  # Remove "task" from command

    # Check for additional arguments
    if len(command) == 0:
        show_error_message("More arguments needed")
        return

    # Dispatch to appropriate handler based on encryption type
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
        case _:
            show_error_message(f"Unknown task \"{command[0]}\"")

def show_error_message(error):
    """
    Display an error message in the chat window.

    Args:
        error (str): Error message to display
    """
    comm.chat_message.emit(f"<Server> {error}")

def show_no_info_from_server():
    """
    Display a message indicating that no response was received from the server.
    """
    comm.chat_message.emit("<INFO> No info received from server, try again later.")

def test_input(text_array):
    """
    Validate task command input parameters.

    Args:
        text_array (list): Command parameters to validate

    Returns:
        int: 1 if valid, 0 if invalid
    """
    if not text_array[-1].isnumeric():
        show_error_message("You must provide a number of words.")
        return 0
    if int(text_array[-1]) < 1 or int(text_array[-1]) > 10000:
        show_error_message("Number must be 1<x<10000.")
        return 0

    send_server_message(f"task {' '.join(text_array)}")
    return 1

def wait_server_messages(number_of_messages, max_time=2) -> bool:
    """
    Wait for a specified number of server messages, clearing previous messages first.

    Args:
        number_of_messages (int): Number of messages to wait for
        max_time (int, optional): Maximum time to wait in seconds. Defaults to 2.

    Returns:
        bool: True if messages received, False if timeout
    """
    server_messages.clear()
    return wait_server_messages_no_empty(number_of_messages, max_time)

def wait_server_messages_no_empty(number_of_messages, max_time=2) -> bool:
    """
    Wait for a specified number of server messages without clearing previous messages.

    Args:
        number_of_messages (int): Number of messages to wait for
        max_time (int, optional): Maximum time to wait in seconds. Defaults to 2.

    Returns:
        bool: True if messages received, False if timeout
    """
    time_waited = 0
    while len(server_messages) < number_of_messages:
        time_waited += 0.1
        if time_waited >= max_time:
            show_no_info_from_server()
            return False
        time.sleep(0.1)
    return True

# endregion

# region Encoding Functions

def difhel(text_array):
    """
    Implement Diffie-Hellman key exchange protocol with the server.

    Args:
        text_array (list): Command parameters
    """
    server_messages.clear()
    send_server_message("task " + ' '.join(text_array))

    # Wait for server response
    if not wait_server_messages_no_empty(1):
        return

    # Generate prime number p and generator g
    p = get_last_prime(random.randint(2, 4999))
    g = get_primitive_root(p)

    server_messages.clear()

    send_server_message(f"{p},{g}")

    # Wait for server confirmation
    if not wait_server_messages_no_empty(2):
        return

    # Check if prime number and generator are accepted
    if not _decode_message(server_messages[0]).__contains__("accepted"):
        print("Error, try again")
        server_messages.clear()
        return

    # Wait for server's half-key
    if not wait_server_messages_no_empty(2):
        return

    server_half_key = int(_decode_message(server_messages[1]))
    my_secret_key = random.randint(1, 5000)
    my_half_key = pow(g, my_secret_key, p)  # g^a mod p

    send_server_message(str(my_half_key))

    # Wait for server to request shared secret
    if not wait_server_messages(1):
        return

    # Calculate shared secret key
    k = pow(server_half_key, my_secret_key, p)  # B^a mod p

    send_server_message(str(k))
    server_messages.clear()

def shift_vigenere_encode(encryption_type: str, text_array: list[str]):
    """
    Encode a message using shift cipher or Vigenere cipher.

    Args:
        encryption_type (str): "shift" or "vigenere"
        text_array (list[str]): Command parameters
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

    # Wait for confirmation
    wait_server_messages(1)

def rsa_encode(text_array):
    """
    Encode a message using RSA encryption.

    Args:
        text_array (list): Command parameters
    """
    if test_input(text_array) == 0: return

    global server_messages

    if not wait_server_messages(2):
        return

    message = _decode_message(server_messages[0])
    x = re.findall("[0-9]+", message)  # Extract numbers from message
    n = int(x[0])
    e = int(x[1])
    message_to_decode = _decode_message(server_messages[1], True)

    message_decoded = b''

    for c in message_to_decode:
        message_decoded += int_encode(pow(c, e, n), 4)
    send_server_message_no_encoding(message_decoded)

    # Wait for confirmation
    wait_server_messages(1)

# endregion

# region Decoding Functions

def shift_vigenere_decode(type, text_array):
    """
    Decode a message using shift cipher or Vigenere cipher.

    Args:
        type (str): "shift" or "vigenere"
        text_array (list): Command parameters
    """
    print('shift_vigenere_decode')

def rsa_decode(text_array):
    """
    Decode a message using RSA decryption.
    Generates a key pair and decrypts the received message.

    Args:
        text_array (list): Command parameters
    """
    if test_input(text_array) == 0: return

    global server_messages

    UPPER_LIMIT = 1000

    # Generate RSA key pair
    p = get_next_prime(random.randint(2, UPPER_LIMIT))
    q = get_next_prime(random.randint(2, UPPER_LIMIT))
    n = p * q
    k = (p - 1) * (q - 1)
    e = get_coprime(k)  # public key
    d = pow(e, -1, k)  # private key (modular multiplicative inverse)

    if not wait_server_messages(1):
        return

    send_server_message(f"{n},{e}")

    # Wait for encoded message
    if not wait_server_messages(1):
        return

    # Decrypt the message
    message_to_decode = _decode_message(server_messages[0], True)

    message_decoded = b''

    for c in message_to_decode:
        message_decoded += int_encode(pow(c, d, n), 4)
    send_server_message_no_encoding(message_decoded)

    wait_server_messages(1)

# endregion

# region Hashing Functions

def hash_command_verify(command):
    """
    Verify a hash value against a message.

    Args:
        command (list): Command parameters
    """
    server_messages.clear()
    send_server_message(f"task {' '.join(command)}")

    if not wait_server_messages_no_empty(3):
        return

    message = server_messages[1]
    hash = server_messages[2]

    server_messages.clear()

    # Compare the computed hash with the provided hash and convert the result to string.
    rslt = str(hashlib.sha256(message).hexdigest() == hash)

    send_server_message(rslt.lower())

    wait_server_messages_no_empty(1)

def hash_command_hash(command):
    """
    Generate a SHA-256 hash for a message.

    Args:
        command (list): Command parameters
    """
    send_server_message(f"task {' '.join(command)}")

    if not wait_server_messages(2):
        return

    message_to_hash = server_messages[1]

    # Generate and send SHA-256 hash
    send_server_message(hashlib.sha256(_decode_message(message_to_hash).encode()).hexdigest())

    wait_server_messages(1)

# endregion

# region Prime Number Utils

def get_coprime(n):
    """
    Find a coprime number for n (gcd(e,n) = 1).
    Used in RSA key generation.

    Args:
        n (int): Number to find coprime for

    Returns:
        int: A number coprime to n
    """
    while True:
        e = random.randint(2, n - 1)
        if math.gcd(e, n) == 1: return e

def is_prime(n: int) -> bool:
    """
    Check if a number is prime using trial division with optimizations.

    Args:
        n (int): Number to check

    Returns:
        bool: True if prime, False otherwise
    """
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
    """
    Find the largest prime number less than or equal to num.

    Args:
        num (int): Upper limit

    Returns:
        int: Largest prime <= num
    """
    curr_num = num - 1
    while curr_num > 3:
        if is_prime(curr_num):
            return curr_num
        curr_num -= 1
    return 3

def get_primitive_root(n):
    """
    Find a primitive root modulo n.
    Used in Diffie-Hellman key exchange.

    Args:
        n (int): Modulus (prime number)

    Returns:
        int: Primitive root of n
    """
    g = 1
    prime_factors = set(get_prime_factors(n - 1))  # Remove duplicates
    ok = False
    while not ok:
        g += 1
        ok = True
        for pf in prime_factors:
            if pow(g, (n - 1) // pf, n) == 1:
                ok = False
    return g

def get_next_prime(n):
    """
    Find the smallest prime number greater than n.

    Args:
        n (int): Lower limit

    Returns:
        int: Smallest prime > n
    """
    num = n + 1
    while not is_prime(num):
        num += 1
    return num

def get_prime_factors(n) -> list[int]:
    """
    Factorize a number into its prime factors.

    Args:
        n (int): Number to factorize

    Returns:
        list[int]: List of prime factors
    """
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

# endregion
