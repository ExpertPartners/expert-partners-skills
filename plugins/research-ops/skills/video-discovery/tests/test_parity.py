import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_every_original_capability_has_a_route_and_named_regression():
    inventory = set()
    for line in (ROOT/'references/methods-used.md').read_text().splitlines():
        if line.startswith('| ') and not line.startswith('| ---'):
            label=line.strip('|').split('|')[0].strip()
            if label not in {'Method','Source/capability'}:
                inventory.add(label)
    entries=json.loads((ROOT/'references/parity.json').read_text())
    assert inventory <= {entry['capability'] for entry in entries}
    assert len(entries)==len({entry['capability'] for entry in entries})
    for entry in entries:
        route=entry['route']
        if '/' in route or route.endswith('.md'):
            assert (ROOT/route).exists(), route
        else:
            parts=route.split('.')
            module=parts.pop(0) if parts[0] in {'review_catalog','probe_media','verify_candidates','discovery_extensions'} else 'video_discovery'
            node=ast.parse((ROOT/'scripts'/f'{module}.py').read_text())
            for name in parts:
                node=next((child for child in node.body if getattr(child,'name',None)==name),None)
                assert node is not None, route
        tests=ast.parse((ROOT/entry['test_file']).read_text())
        assert entry['test'] in {getattr(node,'name',None) for node in tests.body}
