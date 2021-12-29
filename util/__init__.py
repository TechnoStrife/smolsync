import hashlib
from util.struct_file import StructFile
from const import SmolSyncException

from .root_path import RootPath
from .struct_file import StructFile


def save_signature(file: StructFile, signature):
    file.write_bytes(signature)


def check_signature(file: StructFile, signature, file_type):
    sig = file.read_bytes(len(signature))
    if sig != signature:
        raise SmolSyncException(f'{file.name} is not {file_type}')


def hash_file(path):
    BUF_SIZE = 65536
    sha1 = hashlib.sha1()
    with open(path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)

    return sha1.digest()


def human_readable_size(size, decimal_places=1, plus=False):
    plus = '+' * plus
    if abs(size) < 1024:
        return f"{size:{plus}} b"
    for unit in ['b', 'kb', 'mb', 'gb', 'tb', 'pb']:
        if abs(size) < 1024.0 or unit == 'pb':
            break
        size /= 1024.0
    return f"{size:{plus}.{decimal_places}f} {unit}"


def print_tree_line(start: str, last: bool, middle='├── ', end='└── '):
    print(start, end='')
    if last:
        print(end, end='')
        return start + '    '
    else:
        print(middle, end='')
        return start + '│   '

