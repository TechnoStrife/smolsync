import os
import stat
from pathlib import Path
from typing import List, Optional

from const import EasyHash
from util.struct_file import StructFile
from util import RootPath, hash_file


class FileImage:
    def __init__(self, name, path: RootPath, mod, size, created, file_hash=None):
        self.name = name
        self.path = path
        self.mod = int(mod)
        self.size = size
        self.created = created
        self.hash = file_hash
        self.copied_to: Optional[List[FileImage]] = None

    def copy_obj(self):
        return FileImage(self.name, self.path, self.mod, self.size, self.created, self.hash)

    def calc_hash(self):
        self.hash = hash_file(self.path)

    def easy_hash(self) -> EasyHash:
        return (self.created, self.mod, self.size)

    def add_copied_to(self, file: 'FileImage'):
        if self.copied_to is None:
            self.copied_to = []
        self.copied_to.append(file)

    @classmethod
    def from_file(cls, path: RootPath, file_stat: os.stat_result = None, file_hash=None):
        if file_stat is None:
            file_stat = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(file_stat.st_mode):
            raise None
        return cls(path.name, path, file_stat.st_mtime, file_stat.st_size, file_stat.st_ctime, file_hash)

    @classmethod
    def load(cls, file: StructFile, dir: Path):
        self = cls.__new__(cls)
        self.name = file.read_str()
        self.path = dir / self.name
        self.mod = file.read('I')[0]
        self.size = file.read('N')[0]
        self.created = file.read('d')[0]
        self.hash = file.file.read(20)
        self.copied_to = None
        return self

    def save(self, file: StructFile):
        file.write_str(self.name)
        file.write('I', self.mod)
        file.write('N', self.size)
        file.write('d', self.created)
        file.file.write(self.hash)

