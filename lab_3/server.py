import socket
import select
import sys
from header_settings import *

# settings
IP = '127.0.0.1'
PORT = 7777
CODE = 'utf-8'
TIMEOUT = 0.1

sockets_to_read = []  # here lay clients sockets and server socket
sockets_to_write = []  # client's sockets lay here
buf = {}


class Client_queue:
    frags = []
    num = 0
    to_read = True

    def __init__(self, to_read=True, num=0, frags=[], filename, mode):
        self.frags = frags
        self.num = num
        self.to_read = to_read
        self.mode = mode
        self.filename = filename

    def recv_ack(self):
        self.num += 1

    def send_ack(self):
        n = self.num
        self.num += 1
        return n

    def new_frag(self, frag):
        # add check on file end
        self.frags.append(frag)

    def next_send(self):
        return (self.num, self.frags[self.num])


def server():
    print('Server is starting...')
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((IP, PORT))


def new_connection(server_socket):
    client_socket, client_address = server_socket.accept()
    client_socket.setblocking(False)
    sockets_to_read.append(client_socket)
    sockets_to_write.append(client_socket)
    print(f'New connection was established. IP: {client_address[0]} PORT:{client_address[1]}')


def close_connection(current_socket):
    current_socket.shutdown(socket.SHUT_RDWR)
    current_socket.close()
    sockets_to_read.remove(current_socket)
    sockets_to_write.remove(current_socket)
    del buf[current_socket]


def reciever(client_socket):
    req = int(client_socket.recv(2))
    if req == 1 or 2:
        attrs = get_attrs(client_socket)
        if req == 1:
            buf[client_socket] = get_file_frags(
                attrs['filename'], attrs['mode'])
        else:
            buf[client_socket] = Client_queue(
                False, 0, [], attrs['filename'], attrs['mode'])
    elif req == 3:
        frag = get_frag(client_socket)
        buf[client_socket].new_frag(frag)
    else:
        ack = int(client_socket.recv(2))
        buf[client_socket].recv_ack(ack)


def sender(client_socket):
    client = buf[client_socket]
    if client.to_read:
        ack = client.send_ack()
        message = f'{4:>{2}}{ack:>{2}}'
        message = message.encode(CODE)
        client_socket.send(message)
    else:
        frag = client.next_send()
        message = f'{3:>{2}}{frag[0]:>{2}}{frag[1]}'
        message = message.encode(CODE)
        client_socket.send(message)


def get_attrs(client_socket):
    pass


def get_message(client_socket):
    # when we get empty header - we close connection.
    try:
        if not buffers[client_socket]['header_full']:
            header = buffers[client_socket]['header']
            response = wait_full_length(
                client_socket, header, CLIENT_HEADER_LENGTH)

            buffers[client_socket]['header'] = response['data']
            buffers[client_socket]['header_full'] = response['data_full']

            if not buffers[client_socket]['header_full']:
                return

        header = buffers[client_socket]['header'].decode(CODE)
        h_charcount = int(header[:H_LEN_CHAR].strip())
        h_nickname = header[H_LEN_CHAR:].strip()

        if not buffers[client_socket]['message_full']:
            message = buffers[client_socket]['message']
            response = wait_full_length(client_socket, message, h_charcount)

            buffers[client_socket]['message'] = response['data']
            buffers[client_socket]['message_full'] = response['data_full']

            if not buffers[client_socket]['message_full']:
                return

        message = buffers[client_socket]['message'].decode(CODE)
        buffers[client_socket] = {'header': ''.encode(CODE), 'message': ''.encode(CODE),
                                  'header_full': False, 'message_full': False}

        return {'length': h_charcount, 'nickname': h_nickname, 'data': message}

    except Exception as e:
        close_connection(client_socket)
        print(e)
        return


server()
