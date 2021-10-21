import struct
from typing import IO


class StructFile:
    def __init__(self, file: IO, name: str = None):
        self.file = file
        self.name = name

    def read_all(self, count: int):
        buff = b''
        while len(buff) < count:
            buff += self.file.read(count - len(buff))
        return buff

    def read(self, fmt):
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, self.file.read(size))

    def read_bytes(self, n: int):
        return self.file.read(n)

    def read_str(self):
        size = self.read('I')[0]
        return self.read_bytes(size).decode()

    def write(self, fmt, *args):
        self.file.write(struct.pack(fmt, *args))

    def write_bytes(self, b: bytes):
        self.file.write(b)

    def write_str(self, s):
        b = s.encode()
        self.write('I', len(b))
        self.write_bytes(b)
