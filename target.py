from pathlib import Path, PurePath
from typing import Union, Optional

from pathspec import PathSpec

from image import FolderImage
from image.hash_storage import HashStorage
from util import RootPath, StructFile

PathT = Union[str, PurePath]


class Target:
    def __init__(self, name: str, root: PathT, ignore: PathSpec = None):
        if ignore is None:
            ignore = PathSpec([])
        self.name: str = name
        self.root: RootPath = RootPath(root)
        self.data_root: Optional[Path] = None
        self.ignore: PathSpec = ignore
        self.image: Optional[FolderImage] = None
        self.old_image: Optional[FolderImage] = None
        self.hash_storage: Optional[HashStorage] = None

    def image_name(self) -> str:
        return f'{self.name}.image'

    def image_path(self, settings_path: Path) -> Path:
        return settings_path / self.image_name()

    def diff_name(self) -> str:
        return f'{self.name}.diff'

    def diff_path(self, settings_path: Path) -> Path:
        return settings_path / self.diff_name()

    def hash_storage_name(self) -> str:
        return f'{self.name}.hash'

    def hash_storage_path(self, settings_path: Path) -> Path:
        return settings_path / self.hash_storage_name()

    def image_dir(self, dir: Path) -> Path:
        return dir / self.name

    def data_dir(self) -> Path:
        return self.data_root / self.name

    def data_diff(self) -> Path:
        return self.data_root / self.diff_name()

    def load_hash_storage(self, settings_path: Path):
        if self.hash_storage is not None:
            return self.hash_storage
        path = self.hash_storage_path(settings_path)
        if not path.exists() or not path.is_file():
            return None

        with path.open('rb') as f:
            self.hash_storage = HashStorage.load(StructFile(f))
        return self.hash_storage

    def save_hash_storage(self, settings_path: Path):
        path = self.hash_storage_path(settings_path)
        with path.open('wb') as f:
            self.hash_storage.save(StructFile(f))


    def load_old_image(self, setting_path: Path) -> Optional[FolderImage]:
        image_file = self.image_path(setting_path)
        if not image_file.exists() or not image_file.is_file():
            return None

        with image_file.open('rb') as image:
            self.old_image = FolderImage.load(StructFile(image, str(image_file)), self.root)
        return self.old_image

    def make_image(self, show_progress: bool = False) -> FolderImage:
        self.image = FolderImage.image_dir(self.root, self.ignore.match_file)
        if self.hash_storage is None:
            self.hash_storage = HashStorage()
        unhashed = self.hash_storage.apply(self.image)
        self.hash_storage.calc_hash(unhashed, show_progress)
        self.image.name = ''
        return self.image
