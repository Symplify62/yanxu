import hashlib,json
from fastapi.testclient import TestClient
from yanxu.api import create_app
from yanxu.config import Settings


def test_release_manifest_and_immutable_download(tmp_path):
    c=TestClient(create_app(Settings(data_dir=tmp_path/'data')))
    assert c.get('/app/update.json').json()=={'available':False}
    folder=tmp_path/'artifacts';(folder/'releases').mkdir(parents=True)
    data=b'test-package';sha=hashlib.sha256(data).hexdigest();name=f'yanxu-7-{sha[:12]}.apk'
    value=dict(versionCode=7,versionName='0.1.6',minSdk=26,packageName='cn.jiajian.yanxu',url='https://yanxu.qjl666.xyz/app/releases/'+name,size=len(data),sha256=sha,notes='自动更新')
    manifest=folder/'android-update.json';manifest.write_text(json.dumps(value))
    assert c.get('/app/update.json').status_code==503  # Never announce a missing package.
    (folder/'releases'/name).write_bytes(data)
    r=c.get('/app/update.json');assert r.status_code==200 and r.json()['available']
    assert r.headers['cache-control']=='no-store'
    assert c.get('/app/releases/'+name).content==data
    assert c.get('/app/releases/android-update.json').status_code==404
    for change in [dict(url='https://evil.test/'+name),dict(size=100),dict(packageName='evil.app'),dict(versionCode=True),dict(sha256='bad')]:
        manifest.write_text(json.dumps({**value,**change}))
        assert c.get('/app/update.json').status_code==503
    manifest.write_text('{')
    assert c.get('/app/update.json').status_code==503
