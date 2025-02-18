import socket
import threading

HOST = 'vlbelintrocrypto.hevs.ch'
PORT = 6000
connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def _decode_data(text):
    return text.decode()[6:].replace("\x00", "")

def open_connection():
    try:
        connection.connect((HOST, PORT))
    except ConnectionRefusedError as e:
        print("The connection couldn't be established.")
        print(e)
        # créer variable que "window" va chécker pour afficher message d'erreur ou non.
        exit(1)

    print("Connection open")
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