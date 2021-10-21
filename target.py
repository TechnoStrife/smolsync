from pathlib import Path, PurePath
from typing import Union, Optional

from pathspec import PathSpec

from image import FolderImage
from util import RootPath

PathT = Union[str, PurePath]


class Target:
    def __init__(self, name: str, root: PathT, ignore: PathSpec = None):
        if ignore is None:
            ignore = PathSpec([])
        self.name = name
        self.root: RootPath = RootPath(root)
        self.data_root: Optional[Path] = None
        self.ignore = ignore
        self.image = None
        self.old_image = None

    def image_path(self, settings_path: Path) -> Path:
        return settings_path / f'{self.name}.image'

    def diff_name(self) -> str:
        return f'{self.name}.diff'

    def diff_path(self, settings_path: Path) -> Path:
        return settings_path / self.diff_name()

    def image_dir(self, dir: Path) -> Path:
        return dir / self.name

    def data_dir(self) -> Path:
        return self.data_root / self.name

    def data_diff(self) -> Path:
        return self.data_root / self.diff_name()

    def make_image(self):
        self.image = FolderImage.image_dir(self.root, self.ignore.match_file)
        self.image.name = ''
        return self.image
