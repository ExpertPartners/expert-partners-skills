#!/usr/bin/env python3
"""Negative preparation-schema probes against disposable copies only."""
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).absolute().parent
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location('grok_package_validator', HERE / 'validate-package.py')
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

PINS = 'withheld/source-pins.json'
CANDIDATE_PINS = 'candidate/source-inputs.json'
COVERAGE = 'coverage.json'
RECEIPT = 'withheld/receipt-template.json'
GROK_1 = 'withheld/receipt-grok-run-1.json'
GROK_2 = 'withheld/receipt-grok-run-2.json'
ORDINARY_1 = 'withheld/receipt-ordinary-run-1.json'
ORDINARY_2 = 'withheld/receipt-ordinary-run-2.json'

# Each probe names the validator rejection expected from its own mutation.
# Operation tuples are (action, file, path-within-JSON, value). A swap uses
# the other filename as its value and never edits either receipt's contents.
PROBES = [
    ('matching extra pin metadata at both top levels', 'source-pin top-level schema drift', [
        ('set', PINS, ('grader_hint',), 'withheld'),
        ('set', CANDIDATE_PINS, ('grader_hint',), 'withheld'),
    ]),
    ('matching extra pin metadata inside both input entries', 'source-pin input schema or type drift', [
        ('set', PINS, ('inputs', 0, 'grader_hint'), 'withheld'),
        ('set', CANDIDATE_PINS, ('inputs', 0, 'grader_hint'), 'withheld'),
    ]),
    ('candidate-only top-level metadata', 'candidate source-pin top-level schema drift', [
        ('set', CANDIDATE_PINS, ('grader_hint',), 'withheld'),
    ]),
    ('candidate-only input metadata', 'candidate source-pin input schema or type drift', [
        ('set', CANDIDATE_PINS, ('inputs', 0, 'grader_hint'), 'withheld'),
    ]),
    ('missing source-pin top-level field', 'source-pin top-level schema drift', [
        ('remove', PINS, ('hash_algorithm',), None),
    ]),
    ('renamed source-pin top-level field', 'source-pin top-level schema drift', [
        ('rename', PINS, ('hash_algorithm',), 'algorithm'),
    ]),
    ('wrong-type source-pin size', 'source-pin input schema or type drift', [
        ('set', PINS, ('inputs', 0, 'bytes'), '123'),
    ]),
    ('wrong-type candidate path list', 'candidate ordinary path type drift', [
        ('set', CANDIDATE_PINS, ('ordinary_case_input_paths',), 'not a list'),
    ]),
    ('candidate input path mismatch', 'candidate source boundary changed', [
        ('set', CANDIDATE_PINS, ('inputs', 0, 'path'), 'skills/repo-standards/other.md'),
    ]),
    ('source pin SHA mismatch', 'source SHA/size mismatch', [
        ('set', PINS, ('inputs', 0, 'sha256'), '0' * 64),
    ]),
    ('candidate commit mismatch', 'candidate source boundary changed', [
        ('set', CANDIDATE_PINS, ('source_commit',), '0' * 40),
    ]),
    ('extra coverage top-level field', 'coverage top-level schema drift', [
        ('set', COVERAGE, ('result_hint',), 'PASS'),
    ]),
    ('missing coverage case field', 'coverage case schema drift', [
        ('remove', COVERAGE, ('cases', 0, 'mode'), None),
    ]),
    ('renamed coverage variant field', 'coverage variant schema drift', [
        ('rename', COVERAGE, ('cases', 0, 'variants', 0, 'scenario'), 'description'),
    ]),
    ('wrong-type coverage run list', 'coverage required-run type drift', [
        ('set', COVERAGE, ('cases', 0, 'variants', 0, 'required_runs'), '[1, 2]'),
    ]),
    ('wrong-type coverage count', 'coverage counts schema, type or value drift', [
        ('set', COVERAGE, ('counts', 'cases'), True),
    ]),
    ('altered nonempty scenario description', 'coverage scenario descriptions changed', [
        ('set', COVERAGE, ('cases', 0, 'variants', 0, 'scenario'), 'All prerequisites present'),
    ]),
    ('altered nonempty markdown scenario', 'coverage markdown changed', [
        ('replace_text', 'coverage.md', (), ('Digest read, section B.5 qualification omitted', 'Digest read, section B.5 qualification passed')),
    ]),
    ('coverage mode mismatch', 'mode mismatch', [
        ('set', COVERAGE, ('cases', 0, 'mode'), 'auditor'),
    ]),
    ('coverage request hash mismatch', 'request hash mismatch', [
        ('set', COVERAGE, ('cases', 0, 'request_sha256'), '0' * 64),
    ]),
    ('extra aggregate gate result', 'aggregate receipt top-level schema drift', [
        ('set', RECEIPT, ('gate_b_status',), 'PASS'),
    ]),
    ('extra aggregate candidate results', 'aggregate receipt top-level schema drift', [
        ('set', RECEIPT, ('candidate_results',), {'result': 'PASS'}),
    ]),
    ('missing aggregate receipt field', 'aggregate receipt top-level schema drift', [
        ('remove', RECEIPT, ('gate_a_status',), None),
    ]),
    ('renamed aggregate receipt field', 'aggregate receipt top-level schema drift', [
        ('rename', RECEIPT, ('case_run_files',), 'run_files'),
    ]),
    ('wrong-type aggregate counts', 'receipt counts schema, type or value drift', [
        ('set', RECEIPT, ('counts',), []),
    ]),
    ('same-group whole-shard run swap', 'receipt shard filename binding', [
        ('swap', GROK_1, (), GROK_2),
    ]),
    ('cross-group whole-shard swap', 'receipt shard filename binding', [
        ('swap', GROK_1, (), ORDINARY_2),
    ]),
    ('wrong shard group', 'receipt shard filename binding', [
        ('set', ORDINARY_1, ('group',), 'grok'),
    ]),
    ('wrong shard run number', 'receipt shard filename binding', [
        ('set', GROK_1, ('run_number',), 2),
    ]),
    ('case run ID inconsistent with shard filename', 'receipt shard row/filename binding', [
        ('set', GROK_1, ('case_runs', 0, 'run_id'), 'wrong/run-1'),
    ]),
    ('extra nested case-run field', 'case-run schema drift', [
        ('set', GROK_1, ('case_runs', 0, 'candidate_results'), {'result': 'PASS'}),
    ]),
    ('missing nested case-run field', 'case-run schema drift', [
        ('remove', GROK_1, ('case_runs', 0, 'candidate_actor'), None),
    ]),
    ('extra nested variant result field', 'variant result schema drift', [
        ('set', GROK_1, ('case_runs', 0, 'variant_grades', 0, 'candidate_results'), 'PASS'),
    ]),
    ('wrong-type nested variant status', 'variant result fabricated', [
        ('set', GROK_1, ('case_runs', 0, 'variant_grades', 0, 'status'), 1),
    ]),
    ('candidate mode-map mismatch', 'mode distinction lost', [
        ('set', 'candidate/case-modes.json', ('cases', 0, 'mode'), 'auditor'),
    ]),
    ('review-receipt claims candidate runtime', 'review-receipt claims candidate runtime', [
        ('set', 'review-receipt.json', ('candidate_runtime',), 'PASS'),
    ]),
    ('source-manifest claims candidate execution', 'source-manifest claims candidate execution', [
        ('set', 'source-manifest.json', ('candidate_execution',), 'PASS'),
    ]),
        ('extra result file outside candidate', 'preparation package file set changed', [
        ('write_text', 'withheld/receipt-results.json', (), '{"gate_a_status":"PASS"}\n'),
    ]),
    ('extra physical receipt shard', 'preparation package file set changed', [
        ('write_text', 'withheld/receipt-grok-run-3.json', (), '{"status":"PASS"}\n'),
    ]),
    ('unmanifested change to narrative document', 'artifact manifest hash/size mismatch', [
        ('append_text', 'route-assessment.md', (), '\nChanged after manifest review.\n'),
    ]),
    ('missing manifest entry', 'artifact manifest file list changed', [
        ('remove', 'artifact-manifest.json', ('files', 0), None),
    ]),
]


def mutate(package, edits):
    for action, relative, pointer, value in edits:
        path = package / relative
        if action == 'swap':
            other = package / value
            first, second = path.read_bytes(), other.read_bytes()
            path.write_bytes(second)
            other.write_bytes(first)
            continue
        if action == 'write_text':
            path.write_text(value)
            continue
        if action == 'append_text':
            path.write_text(path.read_text() + value)
            continue
        if action == 'replace_text':
            before, after = value
            content = path.read_text()
            if content.count(before) != 1:
                raise AssertionError(f'Expected one text occurrence in {relative}')
            path.write_text(content.replace(before, after))
            continue
        document = validator.read_json(path)
        parent = document
        for key in pointer[:-1]:
            parent = parent[key]
        key = pointer[-1]
        if action == 'set':
            parent[key] = value
        elif action == 'remove':
            del parent[key]
        elif action == 'rename':
            parent[value] = parent.pop(key)
        else:
            raise AssertionError(f'Unknown mutation action: {action}')
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    initial_files = {str(path.relative_to(HERE)): validator.digest(path.read_bytes())
                     for path in HERE.rglob('*') if path.is_file()}
    validator.validate(repo, HERE, emit=False)
    results = []
    with tempfile.TemporaryDirectory(prefix='grok-qualification-regressions-') as temp:
        for index, (name, expected, edits) in enumerate(PROBES):
            copy = Path(temp) / f'probe-{index}'
            shutil.copytree(HERE, copy)
            mutate(copy, edits)
            copy = copy.resolve()
            try:
                validator.validate(repo, copy, emit=False)
            except ValueError as error:
                if expected not in str(error):
                    raise AssertionError(f'{name}: wrong rejection: {error}') from error
            else:
                raise AssertionError(f'{name}: malformed fixture passed')
            results.append({'probe': name, 'result': 'REJECTED', 'reason': expected})
        link = Path(temp) / 'linked-package'
        link.symlink_to(HERE, target_is_directory=True)
        command = [sys.executable, '-B', str(HERE / 'validate-package.py'), '--repo', str(repo), '--package', str(link)]
        linked = subprocess.run(command, text=True, capture_output=True, check=False)
        if linked.returncode != 1 or 'package missing or symlinked' not in linked.stderr:
            raise AssertionError(f'symlink package: wrong result: {linked.returncode}: {linked.stderr}')
        results.append({'probe': 'symlinked package argument', 'result': 'REJECTED', 'reason': 'package missing or symlinked'})
        alias = Path(temp) / 'alias'
        alias.symlink_to(HERE.parent, target_is_directory=True)
        aliased = alias / HERE.name
        command = [sys.executable, '-B', str(HERE / 'validate-package.py'), '--repo', str(repo), '--package', str(aliased)]
        linked = subprocess.run(command, text=True, capture_output=True, check=False)
        if linked.returncode != 1 or 'package missing or symlinked' not in linked.stderr:
            raise AssertionError(f'symlinked ancestor: wrong result: {linked.returncode}: {linked.stderr}')
        results.append({'probe': 'symlinked package ancestor', 'result': 'REJECTED', 'reason': 'package missing or symlinked'})
    final_files = {str(path.relative_to(HERE)): validator.digest(path.read_bytes())
                   for path in HERE.rglob('*') if path.is_file()}
    if final_files != initial_files:
        raise AssertionError('canonical package changed during regression run')
    print(json.dumps({'status': 'PASS', 'additional_negative_probes': len(results), 'results': results, 'canonical_package': 'unchanged'}, indent=2))


if __name__ == '__main__':
    main()
