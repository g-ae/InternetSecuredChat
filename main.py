import socket

HOST = 'vlbelintrocrypto.hevs.ch'
PORT = 6000

def strEncode(type, string):
    # ISC Header + type of message + string length encoded in big-endian
    msg = b'ISC' + type.encode('utf-8') + len(string).to_bytes(2, byteorder='big')

    # Add every char from the string as 3 times \x00 then char encoded in utf-8
    for s in string:
        encoded = s.encode('utf-8')
        msg += (4-len(encoded))*b'\x00' + encoded

    return msg

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.send(strEncode('t', '😂Hel'))
        data = s.recv(1024)

    print(data.decode()[6:].replace("\x00", ""))

if __name__ == '__main__':
    main()