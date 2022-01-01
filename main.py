import datetime
import json
import os
import zipfile
from io import BytesIO
from pathlib import PurePath
from typing import Tuple, Optional, List

import zipp
from pathspec import PathSpec

from args import parser, save_action, status_action, read_action, \
    ArgsType, check_action, apply_action, compare_action
from const import SETTINGS_NAME, SmolSyncException, Signatures
from image import FolderImage, FolderDiff
from image.hash_storage import HashStorage
from summary.changes_summary import ChangesSummary
from target import Target
from util import RootPath, StructFile


def ignore_rules(rules) -> PathSpec:
    if rules is None:
        return PathSpec([])
    assert isinstance(rules, list)
    assert all(isinstance(rule, str) for rule in rules)
    return PathSpec.from_lines('gitwildmatch', rules)


def load_targets(args: ArgsType):
    path = args.settings
    settings_file = path / SETTINGS_NAME
    if not settings_file.exists() or not settings_file.is_file():
        raise SmolSyncException(f'No settings file: {settings_file}')

    settings = json.loads(settings_file.read_text(encoding='utf-8'))

    if args.targets != 'all':
        selected_targets = set(args.targets.split(';'))
        for target in selected_targets:
            if target not in settings:
                raise SmolSyncException(f'Unknown target: {target}')
        for name in list(settings.keys()):
            if name not in selected_targets:
                del settings[name]

    targets = [
        Target(name, path, target_settings['root'], ignore_rules(target_settings.get('ignore')))
        for name, target_settings in settings.items()
    ]
    for target in targets:
        target.load_old_image()

    return targets


def make_images(targets: List[Target]):
    for target in targets:
        target.make_image(use_hash_storage=True, show_progress=True)


def status(args: ArgsType):
    targets = load_targets(args)
    make_images(targets)

    for target in targets:
        print(f'Target {target.name}:')
        if target.old_image is None:
            print('No previously saved state')
            target.image.print(hide_files=args.quiet)
        else:
            diff = FolderDiff.compare(target.image, target.old_image)
            if not args.verbose and not diff.has_changes():
                print('No changes')
            else:
                diff.print(verbose=args.verbose, hide=args.hide, hide_files=args.quiet)

    if args.save:
        for target in targets:
            filename = target.image_path()
            target.image.save(StructFile(filename.open('wb'), str(filename)))


def compare(args: ArgsType):
    root, archive = read_path_for_targets(args, '.image')

    targets = load_targets(args)
    make_images(targets)

    for target in targets:
        with (root / target.image_name()).open('rb') as f:
            image = FolderImage.load(StructFile(f), target.root)
        image.ignore(target.ignore.match_file)

        print(f'Target {target.name}:')
        if args.save:
            hashes = HashStorage.from_image(image)
            for file in target.image.iter_files():
                old_meta = hashes.hashes.get(file.hash)
                new_meta = target.hash_storage.hashes.get(file.hash)
                if old_meta is not None and new_meta is not None:
                    old_file = image[PurePath(old_meta.path)]
                    new_file = target.image[PurePath(new_meta.path)]
                    print(file.path)
                    stat = os.stat(new_file.path)
                    os.utime(new_file.path, None, ns=(stat.st_atime_ns, old_file.mod * 1_000_000_000))
        else:
            diff = FolderDiff.compare(target.image, image)
            if not args.verbose and not diff.has_changes():
                print('No changes')
            else:
                diff.print(verbose=args.verbose, hide=args.hide, hide_files=args.quiet)

    if archive:
        archive.close()

    # if args.save:
    #     for target in targets:
    #         filename = target.image_path(args.settings)
    #         target.image.calc_hash()
    #         target.image.save(StructFile(filename.open('wb'), str(filename)))


def save(args: ArgsType):
    archive = None
    if args.zip:
        if args.path.is_dir():
            args.path /= f'smoldiff_{datetime.date.today().strftime("%d.%m.%y")}.zip'
        elif not args.path.exists() or args.path.is_file():
            if args.path.suffix != '.zip':
                raise SmolSyncException(f'File {args.path} does not end in ".zip". '
                                        f'If you meant a directory, create it first')
        else:
            raise SmolSyncException(f"{args.path} isn't a file or a directory")
        archive = zipfile.ZipFile(args.path, 'w', zipfile.ZIP_DEFLATED)

    targets = load_targets(args)
    make_images(targets)

    for target in targets:
        print(f'Target {target.name}:')

        if args.base is None:
            old_image = target.old_image
            if target.old_image is None:
                print('No previously saved state')
                continue
        else:
            image_file = args.base / target.image_name()
            if not image_file.exists():
                print('No base image')
                continue
            with image_file.open('rb') as f:
                old_image = FolderImage.load(StructFile(f), target.root)
            old_image.ignore(target.ignore.match_file)

        diff = FolderDiff.compare(target.image, old_image)
        if not args.verbose and not diff.has_changes():
            print('No changes')
        else:
            diff.print(verbose=args.verbose, hide_files=args.quiet)
        if not diff.has_changes():
            continue

        diff.remove_unchanged()

        if args.zip:
            with BytesIO() as target_info:
                diff.save(StructFile(target_info, '*mem buffer*'))
                archive.writestr(target.diff_name(), target_info.getvalue())
            diff.copy_modified_to(PurePath(target.name), archive.write)
        else:
            args.path.mkdir(parents=True, exist_ok=True)
            diff_filename = target.diff_path()
            diff.save(StructFile(diff_filename.open('wb'), str(diff_filename)))
            diff.copy_modified_to(args.path / target.name)

    if args.zip:
        archive.close()


def read_path_for_targets(args: ArgsType, suffix: str = '.diff') -> Tuple[RootPath | zipp.Path, Optional[zipfile.ZipFile]]:
    root = RootPath(args.path)
    archive = None
    if args.path.suffix == '.zip' and args.path.is_file():
        archive = zipfile.ZipFile(args.path, 'r', zipfile.ZIP_DEFLATED)
        root = zipp.Path(archive)
    if archive is None and args.path.is_file():
        assert args.path.suffix == suffix
        args.targets = [args.path.stem]
        root = RootPath(args.path.parent)
    elif args.targets == 'all':
        args.targets = ''
        for file in root.iterdir():
            if file.suffix == suffix:
                if args.targets != '':
                    args.targets += ';'
                args.targets += file.stem
    else:
        selected_targets = set(args.targets.split(';'))
        for file in root.iterdir():
            if file.suffix == suffix:
                selected_targets.discard(file.stem)
        if len(selected_targets) != 0:
            raise SmolSyncException(f"Targets {', '.join(selected_targets)}"
                                    f" were not found in {args.path}")
    return root, archive


def check(args: ArgsType):
    root, archive = read_path_for_targets(args)

    targets = load_targets(args)
    make_images(targets)

    for target in targets:
        with (root / target.diff_name()).open('rb') as f:
            diff = FolderDiff.load(StructFile(f), target.root)
        print(f'Target {target.name}:')

        diff.connect_copied_by_path(diff)
        summary = ChangesSummary(diff, target)
        summary.print(args.verbose)

    if archive:
        archive.close()


def apply(args: ArgsType):
    data_root, archive = read_path_for_targets(args)

    targets = load_targets(args)
    make_images(targets)

    for target in targets:
        target.data_root = RootPath(data_root / target.name)
        with data_root.joinpath(target.diff_name()).open('rb') as f:
            diff = FolderDiff.load(StructFile(f), target.root)
        print(f'Target {target.name}:')

        diff.connect_copied_by_path(diff)
        summary = ChangesSummary(diff, target)
        summary.run(args.verbose)

    if archive:
        archive.close()


def read(args: ArgsType):
    if not args.path.exists():
        raise SmolSyncException(f'{args.path} does not exist')
    if not args.path.is_file():
        raise SmolSyncException(f'{args.path} is not a file')
    if args.path.suffix == '.zip':
        print('This zip archive contains:')
        found = False
        with zipfile.ZipFile(args.path, 'r') as archive:
            for filename in archive.namelist():
                if '/' in filename or not filename.endswith('.diff'):
                    continue
                found = True
                print(f'Target {filename[:-5]}:')
                with archive.open(filename) as diff_file:
                    FolderDiff.load(StructFile(diff_file), RootPath()).print()
        if not found:
            print('This is not a smolsync archive')
    else:
        with args.path.open('rb') as f:
            sig = f.read(Signatures.LENGTH)
            f.seek(0)
            if sig == Signatures.IMAGE_SIGNATURE:
                image = FolderImage.load(StructFile(f), RootPath())
                image.print()
            elif sig == Signatures.DIFF_SIGNATURE:
                diff = FolderDiff.load(StructFile(f), RootPath())
                diff.print()
            else:
                print('This file is not a smolsync file')
                if args.verbose:
                    print(f'signature: {repr(sig)}')


status_action.set_defaults(func=status)
compare_action.set_defaults(func=compare)
save_action.set_defaults(func=save)
read_action.set_defaults(func=read)
check_action.set_defaults(func=check)
apply_action.set_defaults(func=apply)
parsed_args = parser.parse_args()
try:
    parsed_args.func(parsed_args)
except SmolSyncException as e:
    print(e.args)
