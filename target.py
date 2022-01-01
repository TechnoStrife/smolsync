from pathlib import Path, PurePath
from typing import Union, Optional

from pathspec import PathSpec

from image import FolderImage
from image.hash_storage import HashStorage
from util import RootPath, StructFile

PathT = Union[str, PurePath]


class Target:
    def __init__(self, name: str, settings_path: PathT, root: PathT, ignore: PathSpec = None):
        if ignore is None:
            ignore = PathSpec([])
        self.name: str = name
        self.settings_path: RootPath = RootPath(settings_path)
        self.root: RootPath = RootPath(root)
        self.data_root: Optional[Path] = None
        self.ignore: PathSpec = ignore
        self.image: Optional[FolderImage] = None
        self.old_image: Optional[FolderImage] = None
        self.hash_storage: Optional[HashStorage] = None

    def image_name(self) -> str:
        return f'{self.name}.image'

    def image_path(self) -> Path:
        return self.settings_path / self.image_name()

    def diff_name(self) -> str:
        return f'{self.name}.diff'

    def diff_path(self) -> Path:
        return self.settings_path / self.diff_name()

    def hash_storage_name(self) -> str:
        return f'{self.name}.hash'

    def hash_storage_path(self) -> Path:
        return self.settings_path / self.hash_storage_name()

    def image_dir(self, dir: Path) -> Path:
        return dir / self.name

    def data_dir(self) -> Path:
        return self.data_root / self.name

    def data_diff(self) -> Path:
        return self.data_root / self.diff_name()

    def load_hash_storage(self):
        if self.hash_storage is not None:
            return self.hash_storage
        path = self.hash_storage_path()
        if not path.exists() or not path.is_file():
            return None

        with path.open('rb') as f:
            self.hash_storage = HashStorage.load(StructFile(f))
        return self.hash_storage

    def save_hash_storage(self):
        path = self.hash_storage_path()
        with path.open('wb') as f:
            self.hash_storage.save(StructFile(f))

    def load_old_image(self) -> Optional[FolderImage]:
        image_file = self.image_path()
        if not image_file.exists() or not image_file.is_file():
            return None

        with image_file.open('rb') as image:
            self.old_image = FolderImage.load(StructFile(image, str(image_file)), self.root)
        return self.old_image

    def make_image(self, use_hash_storage: bool = True, show_progress: bool = False) -> FolderImage:
        self.image = FolderImage.image_dir(self.root, self.ignore.match_file)
        self.image.name = ''

        if use_hash_storage:
            self.load_hash_storage()
            if self.hash_storage is None:
                self.hash_storage = HashStorage()
            unhashed = self.hash_storage.apply(self.image)
            self.hash_storage.calc_hash(unhashed, show_progress)
            self.hash_storage = HashStorage.from_image(self.image)
            self.save_hash_storage()

        return self.image
