import hashlib
import json
from fastapi.testclient import TestClient
from yanxu.api import create_app
from yanxu.config import Settings
from yanxu.identity.__main__ import bootstrap
from yanxu import admin_app_versions


def test_admin_version_lifecycle(tmp_path, monkeypatch):
    settings = Settings(data_dir=tmp_path/'data', environment='testing', public_origin='https://test-yanxu.qjl666.xyz', android_package_name='cn.jiajian.yanxu.testing')
    app = create_app(settings)
    bootstrap(app.state.store, 'admin', 'independent-test-password!', '管理员')
    client = TestClient(app)
    login = client.post('/api/auth/login', json={'username':'admin','password':'independent-test-password!'}).json()
    auth = {'Authorization':'Bearer '+login['accessToken']}
    created = client.post('/api/admin/users', json={'name':'普通账号','username':'version-member','password':'independent-test-password!','roleId':'member'}, headers=auth)
    assert created.status_code == 200
    member_login = client.post('/api/auth/login', json={'username':'version-member','password':'independent-test-password!'}).json()
    member = {'Authorization':'Bearer '+member_login['accessToken']}
    assert client.get('/api/admin/app-versions',headers=member).status_code == 403
    assert client.get('/api/admin/overview',headers=member).status_code == 403
    old, new = b'old-signed-apk', b'new-signed-apk'
    digest = lambda data: hashlib.sha256(data).hexdigest()
    folder = tmp_path/'artifacts'/'releases'; folder.mkdir(parents=True)
    (folder/f'yanxu-7-{digest(old)[:12]}.apk').write_bytes(old)
    manifest = {'packageName':settings.android_package_name,'versionCode':7,'versionName':'0.7','minSdk':26,'size':len(old),'sha256':digest(old),'notes':'old','url':settings.public_origin+f'/app/releases/yanxu-7-{digest(old)[:12]}.apk'}
    (folder.parent/'android-update.json').write_text(json.dumps(manifest))
    def inspect(path):
        data = path.read_bytes()
        if data not in (old,new,b'wrong-signer'): raise ValueError('invalid')
        return {'packageName':settings.android_package_name,'versionCode':7 if data==old else 8,'versionName':'0.7' if data==old else 'test','minSdk':26,'signer':'other' if data==b'wrong-signer' else 'same'}
    monkeypatch.setattr(admin_app_versions,'inspect',inspect)
    assert client.get('/api/admin/app-versions').status_code==401
    assert client.post('/api/admin/app-versions/publish',json={'sha256':digest(new)},headers=member).status_code==403
    assert client.put('/api/admin/app-versions/candidate',content=new,headers={'Content-Type':'application/vnd.android.package-archive'}).status_code==401
    assert client.put('/api/admin/app-versions/candidate',content=b'wrong-signer',headers={**auth,'Content-Type':'application/vnd.android.package-archive'}).status_code==422
    upload = client.put('/api/admin/app-versions/candidate?notes=fix',content=new,headers={**auth,'Content-Type':'application/vnd.android.package-archive'})
    assert upload.status_code==200,upload.text
    assert len(upload.json()['versions'])==2
    assert client.get(f'/app/releases/yanxu-8-{digest(new)[:12]}.apk').status_code==404
    assert client.get('/app/update.json').json()['versionCode']==7
    assert client.post('/api/admin/app-versions/publish',json={'sha256':digest(new),'expectedCurrentSha':None},headers=auth).status_code==409
    published=client.post('/api/admin/app-versions/publish',json={'sha256':digest(new),'expectedCurrentSha':digest(old)},headers=auth)
    assert published.status_code==200,published.text
    assert client.get(f'/app/releases/yanxu-8-{digest(new)[:12]}.apk').content==new
    assert client.get('/app/update.json').json()['versionCode']==8
    assert client.post('/api/admin/app-versions/rollback',json={'sha256':digest(old),'expectedCurrentSha':digest(new)},headers=auth).status_code==200
    assert client.get('/app/update.json').json()['versionCode']==7
    assert [e['action'] for e in client.get('/api/admin/app-versions',headers=auth).json()['events'][:5]]==['rollback','rollback_attempt','publish','publish_attempt','upload']
    (folder/f'yanxu-8-{digest(new)[:12]}.apk').write_bytes(b'tampered')
    assert client.post('/api/admin/app-versions/publish',json={'sha256':digest(new),'expectedCurrentSha':digest(old)},headers=auth).status_code==409
    assert client.get('/app/update.json').json()['versionCode']==7
    assert client.get('/api/admin/overview',headers=auth).json()['appVersion']['versionCode']==7
    with app.state.store.connect(True) as db:
        db.execute("INSERT INTO jobs(recording_id,status) VALUES('sample-running','running')")
        db.execute("INSERT INTO cloud_objects(recording_id,bucket,object_key,status) VALUES('sample-cloud','test','object','failed')")
    overview = client.get('/api/admin/overview',headers=auth).json()['counts']
    assert overview['processing']==1 and overview['cloudFailed']==1
    assert client.get('/api/environment').json()['environment']=='testing'
