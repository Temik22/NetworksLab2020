import socket
import time
import tftp as tf
from threading import Thread

users = dict()


class User:
    def __init__(self):
        self.filename = None
        self.mode = None
        self.block = None
        self.data = b''
        self._t = None
        self.timeout = None
        self._last_package = None

    @property
    def t(self):
        return self._t

    @t.setter
    def t(self, t):
        self.timeout = False
        self._t = t

    @property
    def last_package(self):
        return self._last_package

    @last_package.setter
    def last_package(self, package):
        self._last_package = package
        self.t = time.time()


def server(sock):
    while True:
        try:
            data, addr = tf.recieve(sock)
        except tf.IllegalOPCode:
            tf.send(sock, addr, tf.ERROR.create_with_code(
                tf.Err_code.ILLEGALOP))
            continue
        except socket.timeout:
            check_timeout(sock, users)
            continue
        except:
            print('Server shutdown.')
            break

        if addr not in users:
            users[addr] = User()

        print(f'recieved data from {addr}: {data}')

        if data.opcode == tf.Operation.RRQ:
            users[addr].filename = data.filename
            users[addr].mode = data.mode
            data = tf.read_file(data.filename)
            if data is None:
                error = tf.ERROR.create_with_code(tf.Err_code.NOTFOUND)
                print(f'send {error} to {addr}')
                tf.send(sock, addr, error)
                del users[addr]
                continue

            users[addr].data = data
            users[addr].block = 1
            package = tf.DATA.create(users[addr].block, data[0:512])
            users[addr].last_package = package
            print(f'send {package} to {addr}')
            tf.send(sock, addr, package)

        elif data.opcode == tf.Operation.WRQ:
            users[addr].filename = data.filename
            users[addr].mode = data.mode
            data = tf.read_file(data.filename)
            if data is not None:
                error = tf.ERROR.create_with_code(tf.Err_code.EXIST)
                print(f'send {error} to {addr}')
                tf.send(sock, addr, error)
                del users[addr]
                continue

            tf.send(sock, addr, tf.ACK.create(0))

        elif data.opcode == tf.Operation.ACK:
            users[addr].block = data.block
            accepted_data = users[addr].block * 512
            frame = users[addr].data[accepted_data:accepted_data + 512]
            if len(frame) == 0:
                print(f'File {users[addr].filename} with {len(users[addr].data)} bytes was sent.')
                del users[addr]
                continue

            package = tf.DATA.create(users[addr].block + 1, frame)
            users[addr].last_package = package
            print(f'send {package} to {addr}')
            tf.send(sock, addr, package)

        elif data.opcode == tf.Operation.DATA:
            package = tf.ACK.create(data.block)
            users[addr].last_package = package
            print(f'send {package} to {addr}')
            tf.send(sock, addr, package)
            users[addr].data += data.data
            if data.last:
                tf.write_file(users[addr].filename,
                              users[addr].data, users[addr].mode)
                del users[addr]

        check_timeout(sock, users)


def check_timeout(sock, users):
    for addr, user in list(users.items()):
        if user.t is not None and time.time() - user.t >= tf.SETTINGS['TIMEOUT'] and addr in users:
            if user.timeout:
                print(f'User with addr {addr} deleted because timeouted twice.')
                del users[addr]
            elif user.last_package is not None:
                print(f'User with addr {addr} timeout.')
                user.t = time.time()
                user.timeout = True
                print(f'send {user.last_package} to {addr}')
                tf.send(sock, addr, user.last_package)


def socket_init():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(tuple(tf.SETTINGS['HOST'].values()))
    sock.settimeout(tf.SETTINGS['TIMEOUT'])
    print('Server is ready.')
    return sock


server(socket_init())
