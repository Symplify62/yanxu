"""Optional immutable mirror in an independently verified private Qiniu bucket.

Default storage is the service's private disk. Never fall back to the public
meeting bucket; credentials and storage responses are not surfaced to clients.
"""
from pathlib import Path
import time


class PrivateStorageError(RuntimeError):
    pass


class PrivateQiniu:
    def __init__(self, settings, manager=None):
        self.settings = settings
        self.bucket = getattr(settings, 'voice_private_bucket', '')
        if not self.bucket or self.bucket == settings.qiniu_bucket:
            raise PrivateStorageError('声音档案必须使用独立的私有空间')
        if not settings.qiniu_access_key or not settings.qiniu_secret_key:
            raise PrivateStorageError('未配置私有声音存储凭证')
        from qiniu import Auth, BucketManager
        self.auth = Auth(settings.qiniu_access_key, settings.qiniu_secret_key)
        self.manager = manager or BucketManager(self.auth, preferred_scheme='https')

    def check_private(self):
        metadata, response = self.manager.bucket_info(self.bucket)
        if response.status_code != 200 or not metadata or metadata.get('private') != 1:
            raise PrivateStorageError('声音空间未验证为私有，停止上传')

    def ensure(self, path, key):
        from qiniu import etag
        from qiniu.services.storage.uploaders import ResumeUploaderV2
        self.check_private()  # Check every operation, not only initial setup.
        expected = etag(str(path))
        metadata, response = self.manager.stat(self.bucket, key)
        if response.status_code == 612:
            token = self.auth.upload_token(self.bucket, key, 300, {'insertOnly': 1, 'fsizeLimit': Path(path).stat().st_size})
            uploader = ResumeUploaderV2(self.bucket, auth=self.auth, preferred_scheme='https')
            _, response = uploader.upload(key, file_path=str(path), up_token=token, mime_type='audio/wav')
            if response.status_code not in (200, 614):
                raise PrivateStorageError('私有声音上传暂未完成')
            metadata, response = self.manager.stat(self.bucket, key)
        if response.status_code != 200 or not metadata or metadata.get('hash') != expected or metadata.get('fsize') != Path(path).stat().st_size:
            raise PrivateStorageError('私有声音文件完整性校验失败')

    def delete(self, key):
        _, response = self.manager.delete(self.bucket, key)
        if response.status_code not in (200, 612):
            raise PrivateStorageError('私有声音删除暂未完成')


def archive(store, enrollment_id):
    if not getattr(store.settings, 'voice_private_bucket', ''):
        return
    with store.connect(True) as db:
        row = db.execute('''SELECT e.* FROM voice_enrollments e JOIN voice_profiles p ON p.person_id=e.person_id
          JOIN identity_people i ON i.id=e.person_id WHERE e.id=? AND p.candidate_id=e.id
          AND p.revoked_at IS NULL AND p.revision=e.revision AND i.active=1''', (enrollment_id,)).fetchone()
        if not row:
            raise PrivateStorageError('声音档案授权已改变')
        key = f'voice-enrollments/{row["id"]}/{row["sha256"]}.wav'
        bucket = store.settings.voice_private_bucket
        db.execute('INSERT OR IGNORE INTO voice_objects(enrollment_id,bucket,object_key,status) VALUES(?,?,?,?)',
                   (enrollment_id, bucket, key, 'pending'))
    mirror = PrivateQiniu(store.settings)
    mirror.ensure(row['audio_path'], key)
    with store.connect(True) as db:
        current = db.execute('SELECT status FROM voice_enrollments WHERE id=?', (enrollment_id,)).fetchone()
        db.execute('UPDATE voice_objects SET status=? WHERE enrollment_id=?',
                   ('deleting' if current['status'] in ('revoked', 'superseded') else 'ready', enrollment_id))


def cleanup_one(store):
    with store.connect() as db:
        row = db.execute("SELECT * FROM voice_objects WHERE status='deleting' AND next_at<=? LIMIT 1", (time.time(),)).fetchone()
    if not row:
        return False
    try:
        if row['bucket'] != store.settings.voice_private_bucket:
            raise PrivateStorageError('私有空间配置发生改变，请恢复原配置完成删除')
        PrivateQiniu(store.settings).delete(row['object_key'])
        with store.connect(True) as db:
            db.execute("UPDATE voice_objects SET status='deleted',error=NULL WHERE enrollment_id=?", (row['enrollment_id'],))
    except Exception:
        with store.connect(True) as db:
            db.execute('UPDATE voice_objects SET next_at=?,error=? WHERE enrollment_id=?',
                       (time.time() + 60, '私有对象删除待重试', row['enrollment_id']))
    return True
