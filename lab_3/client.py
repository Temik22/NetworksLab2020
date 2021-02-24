import socket
import tftp as tf

SETTINGS = {
    'MODE': 'octet',
    'LOG': True,
    'CONNECT': ('192.168.0.222', 6969)
}


def change_mode(mode):
    SETTINGS['MODE'] = mode
    print(f'Mode changed to {mode}')


def toggle_logging():
    SETTINGS['LOG'] = not SETTINGS['LOG']
    res = 'enabled' if SETTINGS['LOG'] else 'disabled'
    print(f'Logging {res}')


def connect(addr, port):
    try:
        if addr.count('.') != 3 or not all(0 <= int(val) <= 255 for val in addr.split('.')):
            print('Wrong address view.')
            return

        if (1 <= int(port) <= 65535):
            print('Wrong port view.')
            return

    except e:
        print(f'Unexpected error: {e}')
        return

    SETTINGS['CONNECT'] = (addr, port)


def logging(msg):
    if SETTINGS['LOG']:
        print(msg)


def get(sock, filenames):
    for filename in filenames:
        if tf.read_file(filename) is not None:
            print(f'File {filename} already exist.')
            continue
        rrq = tf.RRQ.create(filename, SETTINGS['MODE'])
        logging(f'Sending {rrq}')
        sock.sendto(rrq, SETTINGS['CONNECT'])
        file = b''
        last = False

        while not last:
            data, _ = tf.recieve(sock)
            logging(f'Recieved {data}')
            if data.opcode == tf.Operation.ERROR:
                break

            if data.opcode == tf.Operation.DATA:
                last = data.last
                ack = tf.ACK.create(data.block)
                file += data.data
                logging(f'Sending {ack}')
                sock.sendto(ack, SETTINGS['CONNECT'])

        if last:
            tf.write_file(filename, file, SETTINGS['MODE'])


def put(sock, filenames):
    for filename in filenames:
        file = tf.read_file(filename)
        # check on netascii todo()
        if file is None:
            print(f'File {filename} does not exist')
            continue

        wrq = tf.WRQ.create(filename, SETTINGS['MODE'])
        logging(f'Sending {wrq}')
        sock.sendto(wrq, SETTINGS['CONNECT'])
        block = 0
        while True:
            data, _ = tf.recieve(sock)
            logging(f'Recieved {data}')
            if data.opcode == tf.Operation.ERROR:
                break
            elif data.opcode == tf.Operation.ACK:
                block = data.block
                frame = file[block * 512:block * 512 + 512]
                package = tf.DATA.create(block + 1, frame)
                print(f'Sending {package}')
                sock.sendto(package, SETTINGS['CONNECT'])
                if package.last:
                    break


def client(sock):
    while True:
        try:
            com = input('> ').lower().split(' ')
        except:
            break

        if com[0] == 'connect':
            if len(com) < 3:
                print('Not enough arguments')
                continue
            connect(*com[1:2])

        elif com[0] == 'binary':
            change_mode('octet')

        elif com[0] == 'ascii':
            change_mode('netascii')

        elif com[0] == 'mode':
            print(SETTINGS['MODE'])

        elif com[0] == 'log':
            toggle_logging()

        elif com[0] == 'get':
            get(sock, com[1:])

        elif com[0] == 'put':
            put(sock, com[1:])

        elif com[0] == 'quit':
            break

        else:
            print('Invalid command')


def sock_init():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return sock


client(sock_init())
