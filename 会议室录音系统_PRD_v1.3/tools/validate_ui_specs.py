#!/usr/bin/env python3
"""Validate page/component/requirement mappings only, not runtime behavior."""
from pathlib import Path
import json,sys
r=Path(__file__).resolve().parents[1]
load=lambda n:json.loads((r/'requirements'/n).read_text())
pages=load('page-specs.json');cases=load('ui-test-cases.json');req={x['id'] for x in load('requirements.json')};errors=[]
pids=[p['id'] for p in pages];cids=[c['id'] for p in pages for c in p['controls']]
if len(set(pids))!=len(pids):errors.append('duplicate page IDs')
if len(set(cids))!=len(cids):errors.append('duplicate component IDs')
page_doc=(r/'docs/design/DES-10-页面级设计与交互规格.md').read_text();test_doc=(r/'docs/acceptance/UI-01-页面与组件测试对应.md').read_text()
for p in pages:
 if f"## {p['id']}｜" not in page_doc:errors.append('missing page prose '+p['id'])
 if not any(t['page_id']==p['id'] for t in cases):errors.append('uncovered page '+p['id'])
 for rid in p['requirements']:
  if rid not in req:errors.append('unknown requirement '+rid)
 for c in p['controls']:
  for key in ['name','position','appearance','action','result','failure']:
   if not c.get(key):errors.append('missing '+key+' '+c['id'])
  if c['id'] not in page_doc:errors.append('missing component prose '+c['id'])
for t in cases:
 if t['page_id'] not in pids:errors.append('unknown page '+t['page_id'])
 if t['product_status']!='未执行':errors.append('overstated product test '+t['id'])
 if f"## {t['id']}｜" not in test_doc:errors.append('missing UI test prose '+t['id'])
 p=next(x for x in pages if x['id']==t['page_id'])
 if set(t['control_ids'])!={c['id'] for c in p['controls']}:errors.append('component coverage mismatch '+t['id'])
 if set(t['requirements'])!=set(p['requirements']):errors.append('requirement coverage mismatch '+t['id'])
print(json.dumps({'scope':'ui_spec_structure_only','result':'PASS' if not errors else 'FAIL','pages':len(pages),'components':len(cids),'ui_specs':len(cases),'errors':errors,'product_tests_executed':0},ensure_ascii=False,indent=2));sys.exit(bool(errors))
