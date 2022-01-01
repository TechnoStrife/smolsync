import os
from pathlib import Path
import argparse
from typing import Union

from const import SETTINGS_NAME

__all__ = [
    'parser',
    'save_action',
    'config_action',
    'status_action',
    'compare_action',
    'read_action',
    'apply_action',
    'check_action',
    'ArgsType'
]


class RootPathAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, Path(values).absolute())


cwd = Path(os.getcwd()).absolute()

if os.name == 'nt':
    default_settings_path = Path(os.path.expandvars('%appdata%')) / 'smolsync'
else:
    default_settings_path = Path.home() / '.smolsync'

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--settings', default=default_settings_path, action=RootPathAction,
                    help='path to the settings folder')
parser.add_argument('-t', default='all', metavar='targets', dest='targets')

action = parser.add_subparsers()

config_action = action.add_parser('config')
config_action.set_defaults(func=lambda args: print(default_settings_path / SETTINGS_NAME))

read_action = action.add_parser('read')
read_action.add_argument('path', action=RootPathAction, help='path to a file')

status_action = action.add_parser('status')
status_action.add_argument('-v', '--verbose', action='store_true', help='show whole tree')
status_action.add_argument('-q', action='store_true', help="don't print files", dest='quiet')
status_action.add_argument('-H', help='hide specific operations', dest='hide')
status_action.add_argument('--save', action='store_true',
                           help='save the current state of the target')

compare_action = action.add_parser('compare')
compare_action.add_argument('-v', '--verbose', action='store_true', help='show whole tree')
compare_action.add_argument('-q', action='store_true', help="don't print files", dest='quiet')
compare_action.add_argument('-H', help='hide specific operations', dest='hide')
compare_action.add_argument('--copy-time', action='store_true', dest='save',
                            help='copy modification time from image to files with matching hash')
compare_action.add_argument('path', action=RootPathAction, default=cwd,
                            help='path to the directory with images')

save_action = action.add_parser('save')
save_action.add_argument('-v', '--verbose', action='store_true', help='show whole tree')
save_action.add_argument('-q', action='count', help="don't print files", dest='quiet')
save_action.add_argument('-z', '--zip', help='save in zip file', action='store_true')
# save_action.add_argument('-C', help='include copies', action='store_true')
save_action.add_argument('--base', action=RootPathAction, default=None,
                         help='base image to compare with')
save_action.add_argument('path', action=RootPathAction,
                         help='path to save the diff')

check_action = action.add_parser('check')
check_action.add_argument('-v', '--verbose', default=0, action='count', help='show all mismatches')
check_action.add_argument('path', action=RootPathAction, default=cwd,
                          help='path to save the diff or the directory with the diffs')

apply_action = action.add_parser('apply')
apply_action.add_argument('-v', '--verbose', default=0, action='count', help='show all mismatches')
apply_action.add_argument('--blind', action='store_true', help='ignore all errors and try to do the best ')
apply_action.add_argument('path', action=RootPathAction, default=cwd,
                          help='path to save the diff or the directory with the diffs')


class ArgsType:
    settings: Path
    base: Path
    targets: str
    verbose: Union[bool, int]
    quiet: bool
    hide: str
    blind: bool
    save: bool
    path: Path
    zip: Path
