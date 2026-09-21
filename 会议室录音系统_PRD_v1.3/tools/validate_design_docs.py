#!/usr/bin/env python3
"""Document consistency checks only; no application or external service calls."""
from pathlib import Path
import json,re,sys
root=Path(__file__).resolve().parents[1]
errors=[]
req=json.loads((root/'requirements/requirements.json').read_text())
tests=json.loads((root/'requirements/test-cases.json').read_text())
order=json.loads((root/'requirements/document-order.json').read_text())
decisions=json.loads((root/'requirements/design-decisions.json').read_text())
rd={x['id']:x for x in req};td={x['id']:x for x in tests}
for r in req:
 for tid in r['test_ids']:
  if tid not in td or r['id'] not in td[tid]['requirements']:errors.append('asymmetric trace '+r['id']+' '+tid)
for t in tests:
 for rid in t['requirements']:
  if rid not in rd or t['id'] not in rd[rid]['test_ids']:errors.append('asymmetric trace '+t['id']+' '+rid)
 if f"### {t['id']}｜" not in (root/'docs/acceptance/TEST-01-验收用例库.md').read_text():errors.append('missing test prose '+t['id'])
for k in ['all_documents','compiled_documents']:
 if len(order[k])!=len(set(order[k])):errors.append('duplicate index '+k)
 for p in order[k]:
  if not (root/p).is_file():errors.append('missing indexed document '+p)
for p in (root/'docs').rglob('*.md'):
 if not p.read_text().lstrip().startswith('#'):errors.append('invalid markdown document body '+str(p.relative_to(root)))
 if str(p.relative_to(root)) not in order['all_documents']:errors.append('unindexed document '+str(p.relative_to(root)))
dec_text=(root/'docs/delivery/DEC-01-决策与实施准备清单.md').read_text()
ids={d['id'] for d in decisions}
if ids!={f'T-{i:02}' for i in range(1,11)}:errors.append('decision set mismatch')
for d in decisions:
 if f"### {d['id']}｜{d['title']}" not in dec_text:errors.append('missing decision prose '+d['id'])
 if d['status'] not in dec_text or d['approved'] or d['verified']:errors.append('decision status mismatch '+d['id'])
 if not d['closure_evidence'] or not d['needed_by']:errors.append('unbounded decision '+d['id'])
core=list((root/'docs/design').glob('*.md'))+[root/'docs/delivery/DEL-01-里程碑与开发工作包.md',root/'docs/delivery/DEL-02-部署运维与上线检查.md',root/'docs/delivery/DEC-01-决策与实施准备清单.md',root/'docs/acceptance/ACC-02-工程测试与发布验证.md']
json_examples=0
for p in core:
 s=p.read_text()
 for block in re.findall(r'```json\s*\n(.*?)\n```',s,re.S):
  try:json.loads(block);json_examples+=1
  except json.JSONDecodeError:errors.append('invalid JSON example '+p.name)
 if any(x in s for x in ['[待填写]','[TODO]','[TBD]']):errors.append('unfilled template '+p.name)
 for i in re.findall(r'(?<![A-Za-z0-9])T-\d{2}(?!\d)',s):
  if i not in ids:errors.append('unknown decision '+i+' in '+p.name)
if any(x['implementation_status']!='未开发' or x['verification_status']!='未执行' for x in req):errors.append('product status overstated')
if any(t['status']!='未执行' for t in tests):errors.append('product tests overstated')
report={'scope':'design_document_consistency_only','result':'PASS' if not errors else 'FAIL','errors':errors,'requirements':len(req),'product_test_specs':len(tests),'design_documents':len(list((root/'docs/design').glob('*.md'))),'indexed_documents':len(order['all_documents']),'technical_decisions':len(decisions),'valid_json_examples':json_examples,'product_tests_executed':0}
print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(bool(errors))
