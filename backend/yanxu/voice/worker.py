import argparse
import json
import threading
import time
from pathlib import Path
from . import repository as repo
from .engine import CommandEngine, EngineUnavailable


def process_one(store, engine=None):
    from .storage import cleanup_one, archive
    cleaned = cleanup_one(store)
    job = repo.claim(store)
    if not job:
        return cleaned
    stopped = threading.Event()
    def beat():
        while not stopped.wait(max(.2, store.settings.lease_seconds / 3)):
            if not repo.heartbeat(store, job['id'], job['owner']):
                return
    thread = threading.Thread(target=beat, daemon=True)
    thread.start()
    try:
        with store.connect() as db:
            table = 'voice_enrollments' if job['kind'] == 'enrollment' else 'recordings'
            row = db.execute(f'SELECT audio_path FROM {table} WHERE id=?', (job['target_id'],)).fetchone()
        if not row or not row['audio_path'] or not Path(row['audio_path']).is_file():
            raise ValueError('任务声音文件不存在')
        result = (engine or CommandEngine(store.settings)).run(job['kind'], row['audio_path'], job['payload'])
        if job['kind'] == 'enrollment':
            archive(store, job['target_id'])
        repo.finish(store, job, result)
    except ValueError as error:
        repo.fail(store, job, str(error)[:120], retryable=False)
    except EngineUnavailable as error:
        repo.fail(store, job, str(error)[:120])
    except Exception:
        repo.fail(store, job, '声音处理暂未完成')
    finally:
        stopped.set()
        thread.join(timeout=2)
    return True


def main():
    from ..config import Settings
    from ..store import Store
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    store = Store(Settings.load())
    repo.initialize(store)
    while True:
        worked = process_one(store)
        if args.once:
            break
        if not worked:
            time.sleep(2)


if __name__ == '__main__':
    main()
