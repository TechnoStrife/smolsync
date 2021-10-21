from typing import TYPE_CHECKING

from const import SmolSyncException
from image import FileDiff, FolderDiff
from util import print_tree_line
from summary.tasks import *


if TYPE_CHECKING:
    from target import Target


class ChangesSummary:
    def __init__(self, diff: FolderDiff, target: 'Target'):
        # diff must have copies connected by `diff.connect_copied()`
        self.target = target
        self.errors = []

        self.tasks = [
            TaskDeleted(target),
            TaskAlreadyCopied(target),

            TaskAdd(target),
            TaskModify(target),
            TaskDelete(target),
            TaskCopy(target),
            TaskGroupSourceDelete(target),

            TaskModifyDeleted(target),
            TaskAlreadyAdded(target),
            TaskMissing(target),
            TaskCopyGroupIsDeleted(target),
            TaskGroupCopy(target),
        ]

        for file in diff.iter():
            summary = FileSummary(file, target.image, target.root, target.data_root)
            for task in self.tasks:
                if task.condition(summary):
                    assert summary.task is None
                    summary.task = task
                    task.append(summary)

    def run(self, verbose=False):
        for task in self.tasks:
            task.run(task.verbosity <= verbose)

    def print(self, verbose=False):
        for task in self.tasks:
            if task.verbosity <= verbose:
                task.print_list()

