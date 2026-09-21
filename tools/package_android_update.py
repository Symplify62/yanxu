#!/usr/bin/env python3
"""Prepare a signed, immutable APK and an atomic-publication manifest. Does not deploy."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

PACKAGE = 'cn.jiajian.yanxu'
ORIGIN = 'https://yanxu.qjl666.xyz'


def inspect(apk, build_tools):
    info = subprocess.check_output([str(build_tools/'aapt'), 'dump', 'badging', str(apk)], text=True)
    match = re.search(r"package: name='([^']+)' versionCode='([0-9]+)' versionName='([^']+)'", info)
    sdk = re.search(r"sdkVersion:'([0-9]+)'", info)
    certs = subprocess.check_output([str(build_tools/'apksigner'), 'verify', '--print-certs', str(apk)], text=True)
    signers = re.findall(r'Signer #[0-9]+ certificate SHA-256 digest: ([a-f0-9]{64})', certs)
    if not match or not sdk or len(signers) != 1:
        raise ValueError('Cannot validate APK metadata/signature')
    return dict(packageName=match[1], versionCode=int(match[2]), versionName=match[3], minSdk=int(sdk[1]), signer=signers[0])


def package(apk, previous, output, build_tools, notes):
    current = inspect(apk, build_tools)
    old = inspect(previous, build_tools)
    if current['packageName'] != PACKAGE or old['packageName'] != PACKAGE or current['signer'] != old['signer']:
        raise ValueError('APK must retain the installed application package and signing key')
    if current['versionCode'] <= old['versionCode']:
        raise ValueError('Version code must increase')
    if not 0 < apk.stat().st_size <= 100*1024*1024:
        raise ValueError('APK size invalid')
    sha = hashlib.sha256(apk.read_bytes()).hexdigest()
    name = f"yanxu-{current['versionCode']}-{sha[:12]}.apk"
    releases = output/'releases';releases.mkdir(parents=True,exist_ok=True)
    target = releases/name
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != sha:
        raise ValueError('Immutable release filename already exists with different bytes')
    shutil.copyfile(apk,target)
    manifest = {k:current[k] for k in ('packageName','versionCode','versionName','minSdk')}
    manifest.update(available=True,url=ORIGIN+'/app/releases/'+name,size=apk.stat().st_size,sha256=sha,notes=notes)
    (output/'android-update.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    # Legacy download link bootstraps 0.1.5 installations; same bytes as the immutable release.
    shutil.copyfile(apk,output/'yanxu-debug.apk')
    return manifest


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('apk',type=Path);p.add_argument('--previous-apk',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--build-tools',required=True,type=Path)
    p.add_argument('--notes',default='改进自动更新与使用体验')
    a=p.parse_args()
    print(json.dumps(package(a.apk,a.previous_apk,a.output,a.build_tools,a.notes),ensure_ascii=False,indent=2))
