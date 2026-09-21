#!/usr/bin/env python3
"""Upload a local audio file through the same resumable API used by Android."""
import argparse,hashlib,json,urllib.request,uuid
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('audio',type=Path);p.add_argument('--base-url',default='http://127.0.0.1:5189');p.add_argument('--title',default='导入录音');p.add_argument('--client-id',default=None);a=p.parse_args()
sha=hashlib.sha256()
with a.audio.open('rb') as f:
 for chunk in iter(lambda:f.read(1024**2),b''):sha.update(chunk)
def call(path,method='GET',data=None,token=None):
 headers={}
 if token:headers['X-Upload-Token']=token
 if isinstance(data,dict):data=json.dumps(data).encode();headers['Content-Type']='application/json'
 req=urllib.request.Request(a.base_url.rstrip('/')+path,data=data,method=method,headers=headers)
 with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
session=call('/api/recordings','POST',{'client_id':a.client_id or str(uuid.uuid4()),'title':a.title,'total_bytes':a.audio.stat().st_size,'sha256':sha.hexdigest(),'extension':a.audio.suffix[1:].lower()})
id=session['id'];token=session['uploadToken'];known={part['part_no'] for part in call('/api/uploads/'+id,token=token)['parts']}
with a.audio.open('rb') as f:
 number=0
 while chunk:=f.read(session['chunkSize']):
  if number not in known:call(f'/api/uploads/{id}/parts/{number}','PUT',chunk,token)
  number+=1
record=call('/api/uploads/'+id+'/complete','POST',token=token)
print(json.dumps({'id':id,'status':record['status'],'duration':record['duration'],'url':a.base_url+'/#/records/'+id},ensure_ascii=False))
