#!/usr/bin/env python3
"""Validate PRD document structure only. No product or service tests are run."""
from pathlib import Path
import json,re,sys
root=Path(__file__).resolve().parents[1]
req=json.loads((root/'requirements/requirements.json').read_text(encoding='utf8'))
tests=json.loads((root/'requirements/test-cases.json').read_text(encoding='utf8'))
errors=[]
rids=[r['id'] for r in req];tids=[t['id'] for t in tests]
if len(rids)!=len(set(rids)):errors.append('duplicate requirement ID')
if len(tids)!=len(set(tids)):errors.append('duplicate test ID')
all_md={str(p.relative_to(root)):p.read_text(encoding='utf8') for p in root.rglob('*.md')}
for r in req:
    path=r['source_document']
    if path not in all_md or f"### {r['id']}｜" not in all_md[path]:errors.append('missing authoritative heading: '+r['id'])
    if not r['test_ids']:errors.append('uncovered requirement: '+r['id'])
    for tid in r['test_ids']:
        if tid not in tids:errors.append('missing test: '+tid)
for t in tests:
    for rid in t['requirements']:
        if rid not in rids:errors.append('unknown test requirement: '+rid)
    if not t.get('steps') or not t.get('expected'):errors.append('empty test: '+t['id'])
for path,text in all_md.items():
    if text.count('```')%2:errors.append('unbalanced code fence: '+path)
    if '\ue200' in text or '\ue202' in text:errors.append('raw tool citation: '+path)
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if re.match(r'^(https?:|mailto:|#)',target):continue
        target=target.split('#')[0]
        if target and not ((root/path).parent/target).exists():errors.append('broken local link: '+path+' -> '+target)
report={'scope':'document_structure_only','requirements':len(req),'test_cases':len(tests),'markdown_files':len(all_md),'errors':errors,'result':'PASS' if not errors else 'FAIL','product_tests_executed':0,'all_product_verification':'未执行'}
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(bool(errors))
