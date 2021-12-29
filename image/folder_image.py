import os
import stat
from pathlib import Path, PurePath
from time import time

from util import RootPath, check_signature, human_readable_size, print_tree_line
from util.struct_file import StructFile
from typing import List, Optional, Dict, Union, Callable
from const import Signatures
from image.file_image import FileImage


class FolderImage:
    size: int

    def __init__(self, name, folders: List['FolderImage'], files: List[FileImage]):
        self.name = name
        self.folders = folders
        self.files = files
        self.size = sum(file.size for file in files) + sum(folder.size for folder in folders)
        self._dict: Optional[Dict[str, Union[FileImage, 'FolderImage']]] = None

    @classmethod
    def image_dir(cls, path: RootPath, ignore_func: Callable[[Path], bool]) -> 'FolderImage':
        self = cls(path.name, [], [])
        for entry in path.iterdir():
            entry_stat = os.stat(entry)
            if stat.S_ISDIR(entry_stat.st_mode):
                folder = cls.image_dir(entry, ignore_func)
                if len(folder.files) + len(folder.folders) != 0:
                    self.folders.append(folder)
                    self.size += folder.size
            elif stat.S_ISREG(entry_stat.st_mode):
                if not ignore_func(entry):
                    file = FileImage.from_file(entry, entry_stat)
                    self.files.append(file)
                    self.size += file.size
        return self

    def calc_hash(self):
        for file in self.files:
            t = time()
            print(file.path, end=' ')
            file.calc_hash()
            print(file.hash, time() - t)
        for folder in self.folders:
            folder.calc_hash()

    @classmethod
    def load(cls, file: StructFile, path: RootPath) -> 'FolderImage':
        check_signature(file, Signatures.IMAGE_SIGNATURE, 'a smolsync image file')
        return cls._load(file, path)

    @classmethod
    def _load(cls, file: StructFile, path: Path):
        self = cls.__new__(cls)
        self.name = file.read_str()
        path = path / self.name
        self.size = file.read('N')[0]
        files_count = file.read('I')[0]
        self.files = []
        self._dict = None
        for _ in range(files_count):
            self.files.append(FileImage.load(file, path))
        dir_count = file.read('I')[0]
        self.folders = []
        for _ in range(dir_count):
            self.folders.append(cls._load(file, path))
        return self

    def save(self, file: StructFile):
        file.write_bytes(Signatures.IMAGE_SIGNATURE)
        self._save(file)

    def _save(self, file: StructFile):
        file.write_str(self.name)
        file.write('N', self.size)
        file.write('I', len(self.files))
        for image_file in self.files:
            image_file.save(file)
        file.write('I', len(self.folders))
        for folder in self.folders:
            folder._save(file)

    def print(self, line_start='', hide_files: bool = False):
        print(f'{self.name}  {human_readable_size(self.size)}')
        count = len(self.folders) + len(self.files) * (not hide_files)
        for z, folder in enumerate(self.folders):
            new_line_start = print_tree_line(line_start, z + 1 == count)
            folder.print(new_line_start, hide_files=hide_files)

        if hide_files:
            return

        for z, file in enumerate(self.files):
            print_tree_line(line_start, z + 1 == len(self.files))
            print(f'{file.name}  {human_readable_size(file.size)}')

    def _make_dict(self):
        if self._dict is not None:
            return
        self._dict = {}
        for folder in self.folders:
            self._dict[folder.name] = folder
        for file in self.files:
            self._dict[file.name] = file

    def __getitem__(self, item: PurePath) -> Union[FileImage, 'FolderImage', None]:
        res = self
        for part in item.parts:
            if not isinstance(res, FolderImage):
                return None
            if res._dict is None:
                res._make_dict()
            res = res._dict.get(part, None)
        return res

