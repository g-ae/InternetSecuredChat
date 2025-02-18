import socket

HOST = 'vlbelintrocrypto.hevs.ch'
PORT = 6000

def strEncode(type, string):
    # ISC Header + type of message + string length encoded in big-endian
    msg = b'ISC' + type.encode('utf-8') + len(string).to_bytes(2, byteorder='big')

    # Add every char from the string as 3 times \x00 then char encoded in utf-8
    for s in string:
        msg += 3*b'\x00' + s.encode('utf-8')

    return msg

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.send(strEncode('t', 'HELlO'))
        data = s.recv(1024)

    print(data.decode())

if __name__ == '__main__':
    main()