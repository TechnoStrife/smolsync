from typing import Tuple


EasyHash = Tuple[str, int, int]

SETTINGS_NAME = 'smolsync.json'


class Signatures:
    IMAGE_SIGNATURE = b'smolimg '
    DIFF_SIGNATURE = b'smoldiff'
    HASH_STORAGE_SIGNATURE = b'smolhash'
    LENGTH = 8


class SmolSyncException(Exception):
    pass


class SmolSyncInfo(Exception):
    pass
