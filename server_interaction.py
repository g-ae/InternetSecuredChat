import socket
import threading

HOST = 'vlbelintrocrypto.hevs.ch'
PORT = 6000
connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connection_state = -1   # -1 not connected yet, 0 connection failed, 1 connected

def _decode_data(text):
    return text.decode()[6:].replace("\x00", "")

def open_connection():
    global connection_state
    try:
        connection.connect((HOST, PORT))
    except (ConnectionRefusedError, socket.gaierror) as e:
        print("The connection couldn't be established.")
        print(e)
        connection_state = 0
        # créer variable que "window" va chécker pour afficher message d'erreur ou non.
        exit(1)

    print("Connection open")
    connection_state = 1
    try:
        t = threading.Thread(target=handle_message_reception)
        t.start()
    except KeyboardInterrupt:
        print("Stopped by Ctrl+C")
    finally:
        if connection:
            connection.close()

def handle_message_reception():
    while True:
        data = connection.recv(65536)
        print(_decode_data(data))

def _str_encode(type, string):
    # ISC Header + type of message + string length encoded in big-endian
    msg = b'ISC' + type.encode('utf-8') + len(string).to_bytes(2, byteorder='big')

    # Add every char from the string as 3 times \x00 then char encoded in utf-8
    for s in string:
        encoded = s.encode('utf-8')
        msg += (4-len(encoded))*b'\x00' + encoded

    return msg

def send_message(text):
    connection.send(_str_encode('t', text))
    print("<You> " + text)