from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from image import FileDiff, FolderImage


class FileSummary:
    def __init__(self, file: FileDiff, image: FolderImage, root: Path, data_root: Path):
        self.diff = file
        self.target_image_root = image
        self.root = root
        self.data_root = data_root
        self.task = None

    @cached_property
    def old_file_image(self):
        return self.target_image_root[self.diff.old.path.from_root()]

    @cached_property
    def new_file_image(self):
        return self.target_image_root[self.diff.new.path.from_root()]

    @cached_property
    def exists_in_data_root(self):
        return self.data_root.joinpath(self.diff.new.path.from_root()).exists()

    @cached_property
    def copies_done(self):
        if self.diff.old.copied_to is None:
            return None
        return [self.target_image_root[x.path.from_root()] is not None for x in self.diff.old.copied_to]
