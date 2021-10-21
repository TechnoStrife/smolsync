import shutil
from abc import abstractmethod, ABCMeta
from pathlib import Path
from typing import TYPE_CHECKING

import zipp

from image import FileDiff, FileImage, FolderImage
from summary.file_summary import FileSummary
from util import print_tree_line

if TYPE_CHECKING:
    from target import Target


class Task(list):
    header: str = "Unnamed task"
    verbosity = 0

    def __init__(self, target: 'Target'):
        super().__init__()
        self.target = target

    @abstractmethod
    def condition(self, file: FileSummary) -> bool: pass

    def run(self, do_print: bool):
        if len(self) == 0:
            return
        if do_print:
            print(self.header)
        last = self[-1]
        for file in self:
            if do_print:
                start = print_tree_line('', file is last)
                self.print_file(file, start)
            self.run_file(file)

    def run_file(self, file: FileSummary):
        pass

    def add_file(self, dest: Path, src: Path):
        dest.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(src, zipp.Path):
            with dest.open('wb') as dest:
                with src.open('rb') as src:
                    while chunk := src.read(4096):
                        dest.write(chunk)
        else:
            shutil.copy2(src, dest)

    def _print_new(self, file: FileSummary, start: str):
        print(file.diff.new.path.from_root().as_posix(), end='')

    def _print_old(self, file: FileSummary, start: str):
        print(file.diff.old.path.from_root().as_posix(), end='')

    def _print_file_copy_list(self, file: FileSummary, start: str):
        print(file.diff.old.path.from_root())
        last = file.diff.old.copied_to[-1]
        for copy in file.diff.old.copied_to:
            print_tree_line(start, copy is last, middle='├─► ', end='└─► ')
            print(copy.path.from_root())

    @abstractmethod
    def print_file(self, file: FileSummary, start: str): pass

    def print_list(self):
        if len(self) == 0:
            return
        print(f'{self.header}:')
        last = self[-1]
        for file in self:
            start = print_tree_line('', file is last)
            self.print_file(file, start)
            print()
            # TODO add check file method to print info
