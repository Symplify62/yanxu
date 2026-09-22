#!/usr/bin/env python3
"""Validate the active AI navigation without traversing historical document packs."""
from collections import deque
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
GUIDES = ROOT / 'frontend/docs/frontend-guides'
SOURCES = [
    ROOT / 'AGENTS.md', ROOT / 'frontend/AGENTS.md', ROOT / 'frontend/CLAUDE.md',
    ROOT / 'README.md', ROOT / 'frontend/README.md', ROOT / 'docs/README.md',
    ROOT / 'docs/phases/phase-01.md',
    ROOT / 'docs/phases/phase-01-pages.md',
    ROOT / 'docs/phases/phase-01-backend.md',
    ROOT / 'config/README.md',
    ROOT / 'backend/README.md', ROOT / 'android/README.md',
    ROOT / 'docs/implementation/phase-one-live.md',
    ROOT / 'docs/implementation/identity-voice-delivery.md',
    ROOT / 'tools/voice-runtime/README.md',
    *sorted((ROOT / 'docs/research').glob('*.md')),
    ROOT / 'docs/repository/workflow.md', ROOT / 'docs/repository/cleanup.md', ROOT / 'frontend/docs/technical-choice.md',
    ROOT / 'frontend/docs/design-lab/selection.md', ROOT / 'frontend/docs/design-lab/README.md',
    ROOT / '会议室录音系统_PRD_v1.3/AGENTS.md',
    ROOT / '会议室录音系统_PRD_v1.3/START_CODEX.md',
    ROOT / '会议室录音系统_PRD_v1.3/README.md',
    ROOT / '会议室录音系统_PRD_v1.3/docs/README.md',
    ROOT / '会议室录音系统_PRD_v1.3/docs/design/DES-05-设计系统与交互规范.md',
    *sorted(GUIDES.glob('*.md')),
]
LINK = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
errors = []
graph = {}
checked = 0
for source in SOURCES:
    if not source.is_file():
        errors.append(f'Missing source: {source.relative_to(ROOT)}')
        continue
    graph[source.resolve()] = []
    for raw in LINK.findall(source.read_text()):
        raw = raw.strip().strip('<>')
        parsed = urlsplit(raw)
        if parsed.scheme or raw.startswith(('#', '//')):
            continue
        relative = unquote(parsed.path)
        if not relative:
            continue
        checked += 1
        target = (source.parent / relative).resolve()
        if not target.is_relative_to(ROOT):
            errors.append(f'Outside project: {source.relative_to(ROOT)} -> {raw}')
        elif not target.exists():
            errors.append(f'Broken link: {source.relative_to(ROOT)} -> {raw}')
        elif target.name not in {p.name for p in target.parent.iterdir()}:
            errors.append(f'Case mismatch: {source.relative_to(ROOT)} -> {raw}')
        else:
            graph[source.resolve()].append(target)

for path, limit in [('AGENTS.md', 80), ('frontend/AGENTS.md', 50)]:
    count = len((ROOT / path).read_text().splitlines())
    if count > limit:
        errors.append(f'{path}: {count} lines exceeds entry budget {limit}')

def distance(start, target):
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        current, depth = queue.popleft()
        if current == target:
            return depth
        for child in graph.get(current, []):
            if child not in seen:
                seen.add(child)
                queue.append((child, depth + 1))
    return None

for guide in sorted(GUIDES.glob('*.md')):
    depth = distance(ROOT / 'AGENTS.md', guide)
    if depth is None or depth > 2:
        errors.append(f'Guide must be reachable within 2 links: {guide.relative_to(ROOT)}')
cases = json.loads((ROOT / 'docs/repository/navigation-cases.json').read_text())
for case in cases:
    depth = distance(ROOT / case['entry'], ROOT / case['target'])
    if depth is None or depth > case['max_hops']:
        errors.append(f"Navigation case failed: {case['task']} (depth={depth})")
if errors:
    print('\n'.join(errors))
    sys.exit(1)
print(f'PASS: {len(SOURCES)} navigation documents, {checked} local links, '
      f'{len(cases)} routing cases; all frontend guides reachable within 2 links.')
print('Scope: file links and navigation structure, not semantic or business acceptance.')
