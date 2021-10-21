import os
from pathlib import PosixPath, WindowsPath


class RootPath(WindowsPath if os.name == 'nt' else PosixPath):
    __slots__ = ('_root_parts',)

    def __init__(self, root=''):
        self._root_parts = len(self._parts)

    def get_root(self) -> 'RootPath':
        return self._from_parts(self._parts[:self._root_parts])

    def from_root(self) -> 'RootPath':
        return self._from_parts(self._parts[self._root_parts:])

    @classmethod
    def _from_parts(cls, args, init=True):
        res = super()._from_parts(args, init)
        res._root_parts = len(res._parts)
        return res

    @classmethod
    def _from_parsed_parts(cls, drv, root, parts, init=True):
        res = super()._from_parsed_parts(drv, root, parts, init)
        res._root_parts = len(res._parts)
        return res

    def _make_child(self, args):
        res = super()._make_child(args)
        res._root_parts = self._root_parts
        return res

    def _make_child_relpath(self, part):
        res = super()._make_child_relpath(part)
        res._root_parts = self._root_parts
        return res
