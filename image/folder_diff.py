import itertools
import os
import shutil
from pathlib import PurePath
from typing import List, Optional, Dict, Set, Callable, Iterable, Union

from const import Signatures, EasyHash
from util import RootPath, StructFile, check_signature, human_readable_size, print_tree_line
from image.folder_image import FolderImage
from image.file_image import FileImage
from image.file_diff import FileDiff


HashFileDict = Dict[EasyHash, FileImage]


class FolderDiff:
    def __init__(self, name, folders: List['FolderDiff'], files: List[FileDiff]):
        self.name = name
        self.folders = folders
        self.files = files
        self.copied_size = 0  # size of the source files copied to recreate the target
        self.change_in_size = 0  # change in size of the target
        self._calc_size()
        self._has_changes = None
        self._has_modified = None
        self._statuses = None
        self._dict: Optional[Dict[str, Union[FileImage, 'FolderImage']]] = None

    def _calc_size(self):
        self.copied_size = 0
        self.change_in_size = 0
        for file in self.files:
            size = file.size()
            self.change_in_size += size
            if file.status in {'M', 'A'}:
                self.copied_size += file.new.size
        for folder in self.folders:
            if not hasattr(folder, 'copied_size'):
                folder._calc_size()
            self.copied_size += folder.copied_size
            self.change_in_size += folder.change_in_size

    def has_changes(self):
        if self._has_changes is None:
            self._has_changes = False
            self._has_changes += sum(file.has_changes() for file in self.files)
            for folder in self.folders:
                self._has_changes += folder.has_changes()
        return bool(self._has_changes)

    def has_modified(self):
        if self._has_modified is None:
            self._has_modified = False
            self._has_modified |= sum(file.is_modified() for file in self.files)
            for folder in self.folders:
                if not self._has_modified:
                    self._has_modified |= folder.has_modified()
        return bool(self._has_modified)

    def statuses(self):
        if self._statuses is not None:
            return self._statuses
        self._statuses = set()
        for folder in self.folders:
            self._statuses |= folder.statuses()
        for file in self.files:
            self._statuses.add(file.status)
        self._statuses.discard('-')
        return self._statuses

    def remove_unchanged(self) -> 'FolderDiff':
        self.files = [file for file in self.files if file.has_changes()]
        self.folders = [
            folder.remove_unchanged()
            for folder in self.folders
            if folder.has_changes()
        ]
        return self

    @classmethod
    def load(cls, file: StructFile, path: RootPath) -> 'FolderDiff':
        check_signature(file, Signatures.DIFF_SIGNATURE, 'a smolsync diff file')
        return cls._load(file, path, root=True)

    @classmethod
    def _load(cls, file: StructFile, path: RootPath, root=False):
        self = cls.__new__(cls)
        self.name = file.read_str()
        if root:
            self.name = ''
        path = path / self.name
        self._has_modified = None
        self._has_changes = None
        self._statuses = None
        self._dict = None
        self.copied_size = file.read('q')[0]
        self.change_in_size = file.read('q')[0]
        files_count = file.read('I')[0]
        self.files = []
        for _ in range(files_count):
            self.files.append(FileDiff.load(file, path))
        dir_count = file.read('I')[0]
        self.folders = []
        for _ in range(dir_count):
            self.folders.append(cls._load(file, path))
        return self

    def save(self, file: StructFile):
        file.write_bytes(Signatures.DIFF_SIGNATURE)
        self._save(file)

    def _save(self, file: StructFile):
        file.write_str(self.name)
        file.write('q', self.copied_size)
        file.write('q', self.change_in_size)
        file.write('I', len(self.files))
        for file_diff in self.files:
            file_diff.save(file)
        file.write('I', len(self.folders))
        for folder in self.folders:
            folder._save(file)

    def connect_copied_by_path(self, root):
        for file in self.files:
            if file.status == 'C':
                copied_from = root[file.old.path.from_root()]
                if copied_from is not None:
                    file.set_copied(copied_from.old)
        for folder in self.folders:
            folder.connect_copied_by_path(root)

    @classmethod
    def compare(cls, new: FolderImage, old: FolderImage, hash_files: bool = False) -> 'FolderDiff':
        self = cls._compare(new, old, hash_files)
        deleted = {}
        self._collect_deleted(deleted)
        self._set_copied(deleted)
        self._calc_size()
        return self

    def _collect_deleted(self, deleted: HashFileDict):
        for file in self.files:
            if file.status == 'D':
                deleted[file.old.easy_hash()] = file.old
        for folder in self.folders:
            folder._collect_deleted(deleted)

    def _set_copied(self, deleted: HashFileDict):
        for file in self.files:
            if file.status == 'A':
                copied_from = deleted.get(file.new.easy_hash(), None)
                if copied_from is not None:
                    file.set_copied(copied_from)
        for folder in self.folders:
            folder._set_copied(deleted)

    @classmethod
    def _compare(cls, new: FolderImage, old: FolderImage, hash_files: bool = False) -> 'FolderDiff':
        name = new.name if new else old.name
        if new is None:
            new = FolderImage(name, [], [])
        if old is None:
            old = FolderImage(name, [], [])

        files = {file.name: [file, None] for file in new.files}
        for file in old.files:
            if file.name in files:
                files[file.name][1] = file
            else:
                files[file.name] = [None, file]
        file_diffs = [FileDiff(file[0], file[1]) for file in files.values()]

        folders = {folder.name: [folder, None] for folder in new.folders}
        for folder in old.folders:
            if folder.name in folders:
                folders[folder.name][1] = folder
            else:
                folders[folder.name] = [None, folder]
        folder_diffs = [FolderDiff._compare(folder[0], folder[1], hash_files) for folder in folders.values()]
        return cls(name, folder_diffs, file_diffs)

    def print(self, line_start='', verbose=False, hide: Iterable[str] = '', hide_files: bool = False):
        print(f'{self.name}  {human_readable_size(self.copied_size)}'
              f'  {human_readable_size(self.change_in_size, plus=True)}')

        def show_folder(folder: FolderDiff):
            if hide is not None and folder.statuses().issubset(hide):
                return False
            return verbose or folder.has_changes()

        def show_file(file: FileDiff):
            if hide is not None and file.status in hide:
                return False
            return file.has_changes()

        folders = list(filter(show_folder, self.folders))
        if hide_files:
            files = []
        else:
            files = list(filter(show_file, self.files))
        last = len(folders) + len(files) - 1

        for z, obj in enumerate(itertools.chain(folders, files)):
            new_line_start = print_tree_line(line_start, z == last)
            if isinstance(obj, FolderDiff):
                obj.print(new_line_start, verbose=verbose, hide=hide, hide_files=hide_files)
            elif isinstance(obj, FileDiff):
                file: FileDiff = obj
                size = file.size()
                print(file.name(), end='')
                if size != 0 and file.status != 'C':
                    print(f'  {human_readable_size(size, plus=True)}', end='')
                print(' ' + file.status)

    def copy_modified_to(self,
                         folder: PurePath,
                         copy_func: Callable[[os.PathLike, os.PathLike], None] = shutil.copy2):
        if not self.has_modified():
            return

        if hasattr(folder, 'mkdir'):  # when saving to archive PurePath is passed
            folder.mkdir(exist_ok=True)  # otherwise Path is passed

        for file in self.files:
            if file.is_modified():
                copy_func(file.new.path, folder / file.new.name)

        for folder_diff in self.folders:
            folder_diff.copy_modified_to(folder / folder_diff.name, copy_func)

    def iter(self) -> Iterable[FileDiff]:
        for file in self.files:
            yield file
        for folder in self.folders:
            yield from folder.iter()

    def _make_dict(self):
        if self._dict is not None:
            return
        self._dict = {}
        for folder in self.folders:
            self._dict[folder.name] = folder
        for file in self.files:
            self._dict[file.name()] = file

    def __getitem__(self, item: PurePath) -> Union[FileDiff, 'FolderDiff', None]:
        res = self
        for part in item.parts:
            if not isinstance(res, FolderDiff):
                return None
            if res._dict is None:
                res._make_dict()
            res = res._dict.get(part, None)
        return res
