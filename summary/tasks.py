from abc import abstractmethod

from summary.file_summary import FileSummary
from summary.task import Task


class TaskMissing(Task):
    header = "Missing files"

    def print_file(self, file: FileSummary, start: str):
        print(file.data_root.joinpath(file.diff.new.path.from_root()).as_posix(), end='')

    def condition(self, file: FileSummary) -> bool:
        return file.diff.status in {'A', 'M'} and not file.exists_in_data_root


class TaskDeleted(Task):
    header = "Already deleted"
    print_file = Task._print_old
    verbosity = 2

    def condition(self, file: FileSummary) -> bool:
        return file.diff.status == 'D' \
               and file.diff.old.copied_to is None \
               and file.old_file_image is None


class TaskAlreadyAdded(Task):
    header = "Existing files to be added"
    print_file = Task._print_new

    def condition(self, file: FileSummary) -> bool:
        return file.diff.status == 'A' \
               and file.exists_in_data_root \
               and file.new_file_image is not None

    def run_file(self, file: FileSummary):
        if file.new_file_image.size != file.diff.new.size:
            print(' - file size differs, please check manually', end='')


class TaskCopyGroupIsDeleted(Task):
    header = 'All files are missing'
    print_file = Task._print_file_copy_list

    def condition(self, file: FileSummary) -> bool:
        return file.diff.status == 'D' \
               and file.diff.old.copied_to is not None \
               and not any(file.copies_done) \
               and file.old_file_image is None


class TaskAlreadyCopied(Task):
    header = 'Already copied/moved'
    print_file = Task._print_file_copy_list
    verbosity = 2

    def condition(self, file: FileSummary) -> bool:
        return file.diff.status == 'D' \
               and file.diff.old.copied_to is not None \
               and all(file.copies_done) \
               and file.old_file_image is None


class TaskDelete(Task):
    header = "Delete"
    print_file = Task._print_old
    verbosity = 1

    def condition(self, file: FileSummary) -> bool:
        return file.diff.status == 'D' \
               and file.diff.old.copied_to is None \
               and file.old_file_image is not None

    def run_file(self, file: FileSummary):
        file.diff.old.path.unlink(missing_ok=True)


class TaskAdd(Task):
    header = "Add"
    print_file = Task._print_new
    verbosity = 1

    def condition(self, file: FileSummary) -> bool:
        return file.diff.status == 'A' \
               and file.exists_in_data_root \
               and file.new_file_image is None

    def run_file(self, file: FileSummary):
        self.add_file(
            dest=file.diff.new.path,
            src=file.data_root.joinpath(file.diff.new.path.from_root())
        )


class TaskModify(TaskAdd):
    header = "Modify"
    verbosity = 1

    def condition(self, file: FileSummary) -> bool:
        return file.diff.status == 'M' \
               and file.exists_in_data_root \
               and file.new_file_image is not None

    def run_file(self, file: FileSummary):
        assert file.diff.new.mod > file.new_file_image.mod
        self.add_file(
            dest=file.diff.new.path,
            src=file.data_root.joinpath(file.diff.new.path.from_root())
        )


class TaskModifyDeleted(TaskAdd):
    header = "Deleted files to be modified"

    def condition(self, file: FileSummary) -> bool:
        return file.diff.status == 'M' \
               and file.exists_in_data_root \
               and file.new_file_image is None


class TaskCopy(Task):
    header = "Copy/move"
    print_file = Task._print_file_copy_list
    verbosity = 1

    def condition(self, file: FileSummary) -> bool:
        return file.diff.status == 'D' \
               and file.diff.old.copied_to is not None \
               and any(file.copies_done) \
               and file.old_file_image is not None

    def run_file(self, file: FileSummary):
        copy_to = file.diff.old.copied_to.copy()
        first = copy_to.pop(0)
        file.diff.old.path.rename(first)
        for copy in copy_to:
            self.add_file(
                dest=copy.path,
                src=first.path
            )


class TaskGroupCopy(Task):
    header = "Copy"
    print_file = Task._print_file_copy_list

    def condition(self, file: FileSummary) -> bool:
        return file.diff.status == 'D' \
               and file.diff.old.copied_to is not None \
               and any(file.copies_done) \
               and file.old_file_image is None

    @abstractmethod
    def run_file(self, file: FileSummary):
        # if file.new_file_image.size != file.diff.new.size:
        #     print(' - file size differs, please check manually', end='')
        pass


class TaskGroupSourceDelete(Task):
    header = "Source is missing but destinations can be copied from another"
    print_file = Task._print_file_copy_list
    verbosity = 1

    def condition(self, file: FileSummary) -> bool:
        return file.diff.status == 'D' \
               and file.diff.old.copied_to is not None \
               and all(file.copies_done) \
               and file.old_file_image is not None

    def run_file(self, file: FileSummary):
        file.diff.old.path.unlink(missing_ok=True)
