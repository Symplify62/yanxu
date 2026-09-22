"""Dedicated remote voice worker. Never accepts an ASR/backup token."""
import argparse
import hashlib
import json
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from .engine import CommandEngine


def process_remote_once(settings, client=None, engine=None):
    base = settings.remote_api.rstrip('/')
    parsed = urlsplit(base)
    if parsed.scheme != 'https' and parsed.hostname not in ('127.0.0.1', 'localhost'):
        raise ValueError('远程声音处理要求HTTPS；本机联调仅允许loopback')
    token = getattr(settings, 'voice_worker_token', '')
    if len(token) < 32:
        raise ValueError('独立声音处理凭证须至少32字符')
    own_client = client is None
    client = client or httpx.Client(base_url=base, headers={'Authorization': 'Bearer ' + token}, timeout=60, follow_redirects=False)
    headers = {'Authorization': 'Bearer ' + token}
    job = None
    stopped = threading.Event()
    thread = None
    try:
        response = client.post('/internal/voice/claim', headers=headers)
        response.raise_for_status()
        job = response.json()['job']
        if not job:
            return False
        lease = {'owner': job['owner']}
        prefix = '/internal/voice/' + job['id']
        def beat():
            while not stopped.wait(max(.2, job['leaseSeconds'] / 3)):
                try:
                    response = client.post(prefix + '/heartbeat', headers=headers, json=lease)
                    if response.status_code == 409:
                        return
                except httpx.HTTPError:
                    pass  # Completion still checks the live lease server-side.
        thread = threading.Thread(target=beat, daemon=True)
        thread.start()
        if job['audioUrl'] != prefix + '/audio':
            raise ValueError('声音任务下载路径无效')
        directory = settings.data_dir / 'private-voices' / 'worker-cache'
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.TemporaryDirectory(prefix='job-', dir=directory) as temporary:
            audio_path = Path(temporary) / 'source.wav'
            digest, size = hashlib.sha256(), 0
            with client.stream('GET', job['audioUrl'], headers=headers, params=lease) as response:
                response.raise_for_status()
                with audio_path.open('wb') as target:
                    for block in response.iter_bytes(1024 * 1024):
                        size += len(block)
                        if size > settings.max_bytes:
                            raise ValueError('声音任务文件超过限制')
                        digest.update(block)
                        target.write(block)
                audio_path.chmod(0o600)
            if digest.hexdigest() != job['payload']['sha256']:
                raise ValueError('声音任务文件校验失败')
            result = (engine or CommandEngine(settings)).run(job['kind'], audio_path, job['payload'])
            response = client.post(prefix + '/complete', headers=headers, json={**lease, 'result': result})
            if response.status_code != 409:
                response.raise_for_status()
        return True
    except Exception as error:
        if job:
            try:
                client.post('/internal/voice/' + job['id'] + '/fail', headers=headers,
                            json={'owner': job['owner'], 'retryable': not isinstance(error, ValueError)})
            except httpx.HTTPError:
                pass
        if isinstance(error, ValueError):
            return bool(job)
        raise
    finally:
        stopped.set()
        if thread:
            thread.join(timeout=2)
        if own_client:
            client.close()


def main():
    from ..config import Settings
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    settings = Settings.load()
    while True:
        try:
            worked = process_remote_once(settings)
        except Exception:
            worked = False
            print('声音任务连接或处理失败，将重试', flush=True)
        if args.once:
            break
        if not worked:
            time.sleep(3)


if __name__ == '__main__':
    main()
