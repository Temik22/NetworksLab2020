import socket
import select
import time
import sys
import json
import threading
from header_settings import *

# settings
IP = '127.0.0.1'
PORT = 7777
CODE = 'utf-8'

sockets = []  # here will lay clients sockets
buffers = {}
clients = []

buffers_empty = {'header': ''.encode(CODE), 'message': ''.encode(CODE),
                 'header_full': False, 'message_full': False}


def server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((IP, PORT))
    server_socket.listen()
    sockets.append(server_socket)
    print(f"Listening for connections ip:{IP}, port:{PORT}")

    while True:
        sockets_to_read, _, sockets_with_exception = select.select(
            sockets, [], sockets)

        for current_socket in sockets_to_read:
            if current_socket == server_socket:
                new_connection(server_socket)
            else:
                message = get_message(current_socket)

                if message:
                    reciever(current_socket, message)
                else:
                    continue

        for current_socket in sockets_with_exception:
            close_connection(current_socket)


def new_connection(server_socket):
    client_socket, client_address = server_socket.accept()
    client_socket.setblocking(False)
    sockets.append(client_socket)
    clients.append(client_socket)
    # added dict that has already initialized as empty buffer place
    buffers[client_socket] = {'header': ''.encode(CODE), 'message': ''.encode(CODE),
                              'header_full': False, 'message_full': False}
    print(f'New connection was established. IP: {client_address[0]} PORT:{client_address[1]}')


def close_connection(current_socket):
    current_socket.shutdown(socket.SHUT_RDWR)
    current_socket.close()
    sockets.remove(current_socket)
    clients.remove(current_socket)
    del buffers[current_socket]
    return


def wait_full_length(current_socket, content, length):
    if len(content) != length:
        content += current_socket.recv(length - len(content))
        if len(content) == length:
            return {'data': content, 'data_full': True}
        else:
            return {'data': content, 'data_full': False}


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


def reciever(client_socket, message):
    # read message
    recieve_time = int(time.time())
    server_formatted_time = get_time(recieve_time)

    print(f"Recieved message from {message['nickname']} at {server_formatted_time}: {message['data']}")

    # get info for server that message has been recieved

    # send this message to all other clients

    header_to_send = f"{message['length']:<{H_LEN_CHAR}}{message['nickname']:<{H_NAME_CHAR}}{recieve_time:<{H_TIME_CHAR}}"
    message_to_send = header_to_send + message['data']
    message_to_send = message_to_send.encode(CODE)

    for client in clients:
        if client != client_socket:
            try:
                client.send(message_to_send)
            except Exception:
                close_connection(client)
                continue


server()
