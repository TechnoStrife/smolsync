from collections import namedtuple
from pathlib import Path
from time import time
from typing import Iterable, Dict, List

from image import FileImage, FolderImage
from util import StructFile, human_readable_size


class HashStorage:
    Key = namedtuple('HashID', ('path', 'modified', 'size'))

    def __init__(self):
        self.files: Dict[HashStorage.Key, bytes] = {}
        self.hashes: Dict[bytes, HashStorage.Key] = {}

    @staticmethod
    def make_key(file: FileImage) -> 'HashStorage.Key':
        return HashStorage.Key(file.path.from_root().as_posix(), file.mod, file.size)

    def add_file(self, file: FileImage):
        key = self.make_key(file)
        self.files[key] = file.hash
        self.hashes[file.hash] = key

    @classmethod
    def load(cls, file: StructFile) -> 'HashStorage':
        self = cls()
        count = file.read('I')[0]
        for _ in range(count):
            path = file.read_str()
            mod = file.read('I')[0]
            size = file.read('N')[0]
            hash = file.file.read(20)
            key = self.Key(path, mod, size)
            self.files[key] = hash
            self.hashes[hash] = key
        return self

    def save(self, file: StructFile):
        file.write('I', len(self.files))
        for key, file_hash in self.files.items():
            file.write_str(key.path)
            file.write('I', key.modified)
            file.write('N', key.size)
            file.file.write(file_hash)

    @classmethod
    def from_image(cls, image: FolderImage) -> 'HashStorage':
        self = cls()
        for file in image.iter_files():
            self.add_file(file)
        return self

    def _apply(self, image: FolderImage, output):
        for file in image.files:
            file_hash = self.files.get(self.make_key(file))
            if file_hash is None:
                output.append(file)
            else:
                file.hash = file_hash
        for folder in image.folders:
            self._apply(folder, output)

    def apply(self, image: FolderImage) -> List[FileImage]:
        res = []
        self._apply(image, res)
        return res

    def calc_hash(self, files: Iterable[FileImage], show_progress: bool = False):
        if show_progress:
            files = list(files)
        t = time()
        size = 0
        for i, file in enumerate(files):
            if show_progress:
                print(f'\r{i+1}/{len(files)} {file.path.from_root()}', end='')
            file.calc_hash()
            self.add_file(file)
            size += file.size
        dt = time() - t
        if show_progress and size > 0 and dt > 0:
            print(f'\r{len(files)}   {human_readable_size(size)}'
                  f'   {dt:.1f}s   {human_readable_size(size / dt)}/s')
