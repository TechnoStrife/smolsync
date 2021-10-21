from pathlib import PurePosixPath

from util.struct_file import StructFile
from util import RootPath
from image.file_image import FileImage


class FileDiff:
    def __init__(self, new: FileImage, old: FileImage):
        self.new = new
        self.old = old
        if new is old:
            self.status = '-'
        elif new is None:
            self.status = 'D'  # Deleted
        elif old is None:
            self.status = 'A'  # Added
        elif new.mod != old.mod or new.size != old.size or new.hash is not None and new.hash != old.hash:
            self.status = 'M'  # Modified
        # elif new.hash is None or old.hash is None:
        #     return '?'
        else:
            self.status = '-'  # unchanged

    def set_copied(self, file: FileImage):
        self.status = 'C'  # Copied
        self.old = file
        self.old.add_copied_to(self.new)

    def size(self):
        new_size = self.new.size if self.new is not None else 0
        old_size = self.old.size if self.old is not None and self.status != 'C' else 0
        return new_size - old_size

    def name(self):
        if self.new is not None:
            return self.new.name
        return self.old.name

    def has_changes(self):
        return self.status != '-'

    def is_modified(self):
        return self.status in {'A', 'M'}

    @classmethod
    def load(cls, file: StructFile, folder: RootPath):
        self = cls.__new__(cls)
        self.status = chr(file.read('B')[0])
        self.old = self.new = None
        if self.status == 'D':
            self.old = FileImage.load(file, folder)
        elif self.status == 'A':
            self.new = FileImage.load(file, folder)
        elif self.status == 'C':
            self.new = FileImage.load(file, folder)
            self.old = self.new.copy_obj()
            path = file.read_str()
            path = PurePosixPath(*PurePosixPath(path).parts[1:])  # FIXME
            self.old.path = folder.get_root() / PurePosixPath(path)
        elif self.status == 'M':
            self.new = FileImage.load(file, folder)
            self.old = FileImage.load(file, folder)
        elif self.status == '-':
            self.new = self.old = FileImage.load(file, folder)
        return self

    def save(self, file: StructFile):
        status = self.status
        file.write('B', ord(status))
        if status == 'D':
            self.old.save(file)
        elif status == 'A':
            self.new.save(file)
        elif status == 'C':
            self.new.save(file)
            file.write_str(self.old.path.from_root().as_posix())
        elif status == 'M':
            self.new.save(file)
            self.old.save(file)
        elif status == '-':
            self.new.save(file)
