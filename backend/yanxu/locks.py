from contextlib import contextmanager
from pathlib import Path
import os


if os.name == "nt":
    import msvcrt

    def lock_file(handle, blocking=True):
        mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
        pos = handle.tell()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), mode, 1)
        except OSError as exc:
            raise BlockingIOError() from exc
        finally:
            handle.seek(pos)

    def unlock_file(handle):
        pos = handle.tell()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            handle.seek(pos)

else:
    import fcntl

    def lock_file(handle, blocking=True):
        flags = fcntl.LOCK_EX | (fcntl.LOCK_NB if not blocking else 0)
        fcntl.flock(handle, flags)

    def unlock_file(handle):
        fcntl.flock(handle, fcntl.LOCK_UN)


@contextmanager
def file_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        lock_file(handle)
        try:
            yield
        finally:
            unlock_file(handle)
