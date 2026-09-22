"""Private, bounded SQLite + enrollment WAV recovery bundles.

No tar extraction API is used. A database write reservation spans snapshot and
sample copies, so enrollment replacement/revocation cannot race that snapshot.
Public meeting audio remains backed by the separately verified object store.
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import tarfile
import tempfile
from pathlib import Path

MAX_DATABASE_BYTES = 512 * 1024**2
MAX_SAMPLE_BYTES = 16 * 1024**2
MAX_BUNDLE_BYTES = 2 * 1024**3
MAX_MANIFEST_BYTES = 4 * 1024**2
MAX_FILES = 10000
SAMPLE_NAME = re.compile(r'^private-voices/([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})\.wav$')
HASH = re.compile(r'^[0-9a-f]{64}$')


def _digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _entry(path, name):
    return {'path': name, 'bytes': path.stat().st_size, 'sha256': _digest(path)}


def _sample_rows(db):
    db.row_factory = sqlite3.Row
    return db.execute('''SELECT e.id,e.audio_path,e.sha256,e.total_bytes FROM voice_enrollments e
      JOIN voice_profiles p ON p.person_id=e.person_id
      WHERE e.audio_path IS NOT NULL AND e.status!='revoked' AND p.revoked_at IS NULL''').fetchall()


def _copy_checked(source, destination, size, digest):
    # Reject symlinks, including a swapped final component. Parent is checked by
    # the caller against the private directory and canonical enrollment UUID.
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != size:
            raise ValueError('私有样本长度或文件类型不符')
        hashed = hashlib.sha256()
        count = 0
        with os.fdopen(fd, 'rb', closefd=False) as src, destination.open('xb') as dst:
            destination.chmod(0o600)
            while block := src.read(1024 * 1024):
                count += len(block)
                if count > size:
                    raise ValueError('私有样本长度已改变')
                hashed.update(block)
                dst.write(block)
            dst.flush()
            os.fsync(dst.fileno())
        if count != size or hashed.hexdigest() != digest:
            raise ValueError('私有样本完整性验证失败')
    finally:
        os.close(fd)


def create_bundle(store, output):
    """Publish only a validated private bundle; an incomplete source fails closed."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if output.exists():
        raise ValueError('备份文件已存在')
    temporary_archive = None
    try:
        with tempfile.TemporaryDirectory(prefix='.private-backup-', dir=output.parent) as temp:
            stage = Path(temp)
            database = stage / 'yanxu.sqlite3'
            voices = stage / 'private-voices'
            voices.mkdir(mode=0o700)
            with store.connect(True):
                # A second connection can backup the committed snapshot while the
                # first holds the write reservation. Backup on the writing
                # connection itself would wait for its own transaction.
                with store.connect() as source, sqlite3.connect(database) as copied:
                    source.backup(copied)
                database.chmod(0o600)
                if not 0 < database.stat().st_size <= MAX_DATABASE_BYTES:
                    raise ValueError('数据库超过私有备份限制')
                with sqlite3.connect(database) as snapshot:
                    if snapshot.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                        raise ValueError('数据库备份校验失败')
                    rows = _sample_rows(snapshot)
                if len(rows) > MAX_FILES - 1:
                    raise ValueError('私有样本数量超过备份限制')
                total = database.stat().st_size + sum(row['total_bytes'] for row in rows)
                if total > MAX_BUNDLE_BYTES - MAX_MANIFEST_BYTES - 1024 * MAX_FILES:
                    raise ValueError('私有备份超过大小限制')
                if shutil.disk_usage(output.parent).free < total * 3 + store.settings.min_free_bytes:
                    raise ValueError('磁盘空间不足以验证私有备份')
                entries = [_entry(database, 'yanxu.sqlite3')]
                root = store.settings.data_dir / 'private-voices'
                if root.is_symlink():
                    raise ValueError('私有样本目录不允许符号链接')
                for row in rows:
                    name = 'private-voices/' + row['id'] + '.wav'
                    if not SAMPLE_NAME.fullmatch(name) or not 0 < row['total_bytes'] <= MAX_SAMPLE_BYTES or not HASH.fullmatch(row['sha256']):
                        raise ValueError('私有样本元数据无效')
                    source = Path(row['audio_path'])
                    if source != root / (row['id'] + '.wav') or source.parent.resolve() != root.resolve():
                        raise ValueError('私有样本路径超出授权目录')
                    target = stage / name
                    _copy_checked(source, target, row['total_bytes'], row['sha256'])
                    entries.append({'path': name, 'bytes': row['total_bytes'], 'sha256': row['sha256']})
            manifest = {'format': 'yanxu-private-backup', 'version': 1,
                        'createdAt': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'files': entries}
            manifest_file = stage / 'manifest.json'
            manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding='utf-8')
            manifest_file.chmod(0o600)
            if manifest_file.stat().st_size > MAX_MANIFEST_BYTES:
                raise ValueError('私有备份清单过大')
            fd, archive_name = tempfile.mkstemp(prefix='.bundle-', suffix='.tar', dir=output.parent)
            os.close(fd)
            temporary_archive = Path(archive_name)
            with tarfile.open(temporary_archive, 'w', format=tarfile.USTAR_FORMAT) as archive:
                for name in ['manifest.json'] + [entry['path'] for entry in entries]:
                    path = stage / name
                    member = tarfile.TarInfo(name)
                    member.mode, member.size = 0o600, path.stat().st_size
                    with path.open('rb') as stream:
                        archive.addfile(member, stream)
            if temporary_archive.stat().st_size > MAX_BUNDLE_BYTES:
                raise ValueError('私有备份超过大小限制')
            validate_bundle(temporary_archive)
            with temporary_archive.open('rb') as stream:
                os.fsync(stream.fileno())
            os.replace(temporary_archive, output)
            return output
    finally:
        if temporary_archive:
            temporary_archive.unlink(missing_ok=True)


def _manifest(value):
    if not isinstance(value, dict) or value.get('format') != 'yanxu-private-backup' or value.get('version') != 1:
        raise ValueError('私有备份格式无效')
    entries = value.get('files')
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_FILES:
        raise ValueError('私有备份清单无效')
    indexed = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {'path', 'bytes', 'sha256'}:
            raise ValueError('私有备份文件描述无效')
        name = entry['path']
        if not isinstance(name, str) or (name != 'yanxu.sqlite3' and not SAMPLE_NAME.fullmatch(name)) or name in indexed:
            raise ValueError('私有备份文件路径无效')
        maximum = MAX_DATABASE_BYTES if name == 'yanxu.sqlite3' else MAX_SAMPLE_BYTES
        if type(entry['bytes']) is not int or not 0 < entry['bytes'] <= maximum or not isinstance(entry['sha256'], str) or not HASH.fullmatch(entry['sha256']):
            raise ValueError('私有备份文件校验信息无效')
        indexed[name] = entry
    if 'yanxu.sqlite3' not in indexed or sum(e['bytes'] for e in indexed.values()) > MAX_BUNDLE_BYTES:
        raise ValueError('私有备份数据库缺失或总量超限')
    return indexed


def _restore_into(bundle, target, mapped_target):
    if not 0 < bundle.stat().st_size <= MAX_BUNDLE_BYTES:
        raise ValueError('私有备份大小无效')
    (target / 'private-voices').mkdir(mode=0o700)
    with tarfile.open(bundle, 'r|') as archive:
        first = archive.next()
        if not first or first.name != 'manifest.json' or not first.isreg() or not 0 < first.size <= MAX_MANIFEST_BYTES:
            raise ValueError('私有备份清单缺失')
        manifest = json.load(archive.extractfile(first))
        entries = _manifest(manifest)
        seen = set()
        while member := archive.next():
            name = member.name
            if name not in entries or name in seen or not member.isreg() or member.size != entries[name]['bytes']:
                raise ValueError('私有备份包含未授权或重复文件')
            seen.add(name)
            path = target / name  # Name is strictly allowlisted, never archive-driven extraction.
            with path.open('xb') as out:
                path.chmod(0o600)
                source = archive.extractfile(member)
                digest, size = hashlib.sha256(), 0
                while block := source.read(1024 * 1024):
                    size += len(block)
                    if size > entries[name]['bytes']:
                        raise ValueError('私有备份文件长度超限')
                    digest.update(block)
                    out.write(block)
            if size != entries[name]['bytes'] or digest.hexdigest() != entries[name]['sha256']:
                raise ValueError('私有备份文件校验失败')
        if seen != set(entries):
            raise ValueError('私有备份文件不完整')
    database = target / 'yanxu.sqlite3'
    with sqlite3.connect(database) as db:
        db.execute('PRAGMA trusted_schema=OFF')
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('私有备份数据库损坏')
        rows = _sample_rows(db)
        required = {'private-voices/' + row['id'] + '.wav': row for row in rows}
        if set(required) != seen - {'yanxu.sqlite3'}:
            raise ValueError('私有备份文件与数据库引用不一致')
        for name, row in required.items():
            if entries[name]['sha256'] != row['sha256'] or entries[name]['bytes'] != row['total_bytes']:
                raise ValueError('私有备份样本与数据库校验信息不一致')
        # Absolute source paths cannot be reused during restoration. Revoked and
        # incomplete rows deliberately receive no audio pointer.
        db.execute('UPDATE voice_enrollments SET audio_path=NULL')
        for name, row in required.items():
            db.execute('UPDATE voice_enrollments SET audio_path=? WHERE id=?', (str(mapped_target / name), row['id']))
    return {'samples': len(rows), 'files': len(entries), 'database': str(mapped_target / 'yanxu.sqlite3')}


def restore_bundle(bundle, destination):
    """Restore only to a new directory. Existing production data is never overwritten."""
    bundle, destination = Path(bundle), Path(destination).resolve()
    if destination.exists():
        raise ValueError('恢复目录必须不存在，禁止覆盖已有资料')
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    stage = Path(tempfile.mkdtemp(prefix='.restore-', dir=destination.parent))
    try:
        result = _restore_into(bundle, stage, destination)
        if destination.exists():
            raise ValueError('恢复目录已存在')
        os.rename(stage, destination)
        return result
    except (tarfile.TarError, sqlite3.Error, json.JSONDecodeError, UnicodeError, EOFError) as error:
        raise ValueError('私有备份无法通过恢复验证') from error
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def validate_bundle(bundle):
    with tempfile.TemporaryDirectory(prefix='.verify-', dir=Path(bundle).parent) as temp:
        result = restore_bundle(bundle, Path(temp) / 'restored')
        return {'samples': result['samples'], 'files': result['files'], 'verified': True}


def main():
    import argparse
    parser = argparse.ArgumentParser(description='验证或恢复私有备份；恢复目标须为不存在的新目录')
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--restore-to', type=Path)
    args = parser.parse_args()
    result = restore_bundle(args.bundle, args.restore_to) if args.restore_to else validate_bundle(args.bundle)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
