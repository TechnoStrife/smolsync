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

    @classmethod
    def load(cls, file: StructFile):
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

    def _apply(self, image: FolderImage, output):
        for file in image.files:
            key = self.Key(str(file.path.from_root()), file.mod, file.size)
            file_hash = self.files.get(key, None)
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
            key = self.Key(str(file.path.from_root()), file.mod, file.size)
            self.files[key] = file.hash
            self.hashes[file.hash] = key
            size += file.size
        if show_progress and size > 0:
            dt = time() - t
            print(f'\r{len(files)}   {human_readable_size(size)}'
                  f'   {dt:.1f}s   {human_readable_size(size / dt)}/s')
