from enum import Enum

SETTINGS = {
    'HOST': {
        'ADDR': '0.0.0.0',
        'PORT': 6969
    },
    'BUFFERSIZE': 1024
}


class Operation(Enum):
    RRQ = 1
    WRQ = 2
    DATA = 3
    ACK = 4
    ERROR = 5


class Err_code(Enum):
    NOTDEFINED = 0
    NOTFOUND = 1
    ACCESSVIOLATION = 2
    DISKFULL = 3
    ILLEGALOP = 4
    UNKNOWN = 5
    EXIST = 6
    NOUSER = 7


class IllegalOPCode(Exception):
    pass  # exception for such error


def get_err_message(code):
    msg = ''
    if code == Err_code.NOTDEFINED:
        msg = 'Not defined, see error message (if any).'
    elif code == Err_code.NOTFOUND:
        msg = 'File not found.'
    elif code == Err_code.ACCESSVIOLATION:
        msg = 'Access violation.'
    elif code == Err_code.DISKFULL:
        msg = 'Disk full or allocation exceeded.'
    elif code == Err_code.ILLEGALOP:
        msg = 'Illegal TFTP operation.'
    elif code == Err_code.UNKNOWN:
        msg = 'Unknown transfer ID.'
    elif code == Err_code.EXIST:
        msg = 'File already exists.'
    elif code == Err_code.NOUSER:
        msg = 'No such user.'
    return msg


def int_to_n_bytes(num, n=2):
    return num.to_bytes(n, 'big')


def bytes_to_int(bytelist):
    return int.from_bytes(bytelist, 'big')


def netascii(data, to):
    pass  # encode data from or to netascii


class RRQ:
    def __init__(self, data):
        self.opcode = Operation(bytes_to_int(data[0:2]))
        attrs = data[2:].split(b'\x00')
        self.filename = attrs[0].decode()
        self.mode = attrs[1].decode()

    @staticmethod
    def create(filename, mode):
        return RRQ(
            int_to_n_bytes(Operation.RRQ.value)
            + filename.encode()
            + int_to_n_bytes(0, 1)
            + mode.encode()
            + int_to_n_bytes(0, 1)
        )

    @property
    def package(self):
        return (
            int_to_n_bytes(self.opcode.value)
            + self.filename.encode()
            + int_to_n_bytes(0, 1)
            + self.mode.encode()
            + int_to_n_bytes(0, 1)
        )

    def __str__(self):
        return f'RRQ. filename: {self.filename}, mode: {self.mode}'


class WRQ(RRQ):
    @staticmethod
    def create(filename, mode):
        return WRQ(
            int_to_n_bytes(Operation.WRQ.value)
            + filename.encode()
            + int_to_n_bytes(0, 1)
            + mode.encode()
            + int_to_n_bytes(0, 1)
        )

    def __str__(self):
        return f'WRQ. filename: {self.filename}, mode: {self.mode}'


class DATA:
    def __init__(self, data):
        self.opcode = Operation.DATA
        self.block = bytes_to_int(data[2:4])
        self.data = data[4:]
        self.last = True if len(self.data) < 512 else False

    @property
    def package(self):
        return int_to_n_bytes(self.opcode.value) + int_to_n_bytes(self.block) + self.data

    @staticmethod
    def create(block, data):
        return DATA(
            int_to_n_bytes(Operation.DATA.value)
            + int_to_n_bytes(block)
            + data
        )

    def __str__(self):
        return f'DATA. Block: {self.block}, data: {self.data}'


class ACK:
    def __init__(self, data):
        self.opcode = Operation.ACK
        self.block = bytes_to_int(data[2:4])

    @staticmethod
    def create(block):
        return ACK(int_to_n_bytes(Operation.ACK.value) + int_to_n_bytes(block))

    @property
    def package(self):
        return int_to_n_bytes(self.opcode) + int_to_n_bytes(self.block)

    def __str__(self):
        return f'ACK. Block: {self.block}'


class ERROR:
    def __init__(self, data):
        self.opcode = Operation.ERROR
        self.code = Err_code(bytes_to_int(data[2:4]))
        msg = data[4:].split(b'\x00')
        self.message = msg[0].decode()

    @staticmethod
    def create_with_code(code):
        return ERROR(
            int_to_n_bytes(Operation.ERROR.value)
            + int_to_n_bytes(code.value)
            + get_err_message(code).encode()
            + int_to_n_bytes(0, 1)
        )

    @ property
    def package(self):
        return (
            int_to_n_bytes(self.opcode.value)
            + int_to_n_bytes(self.code)
            + self.message.encode()
            + int_to_n_bytes(0, 1)
        )


opcode_to_package = {
    Operation.RRQ: RRQ,
    Operation.WRQ: WRQ,
    Operation.DATA: DATA,
    Operation.ACK: ACK,
    Operation.ERROR: ERROR
}


def read_file(filename, server=True):
    try:
        with open(('files/' if server else '') + filename, 'wb') as f:
            data = f.read()
        return data
    except:
        return None


def write_file(filename, data, mode, server=True):
    if mode == 'netascii':
        with open(('files/' if server else '') + filename, 'wb') as f:
            pass  # f.write() netascii to bytes function
    elif mode == 'octet':
        with open(('files/' if server else '') + filename, 'wb') as f:
            f.write(data)


def recieve(sock):
    data, addr = sock.recvfrom(SETTINGS['BUFFERSIZE'])
    try:
        opcode = bytes_to_int(data[:2])
        obj = opcode_to_package[Operation(opcode)](data)
    except:
        raise IllegalOPCode
    return obj, addr


def send(sock, addr, data):
    sock.sendto(data.package, addr)
