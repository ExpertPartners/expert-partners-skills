#!/usr/bin/env python3
"""Negative preparation-schema probes against disposable copies only."""
import argparse
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
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
    validator.validate(repo, HERE, emit=False)
    results = []
    with tempfile.TemporaryDirectory(prefix='grok-qualification-regressions-') as temp:
        for index, (name, expected, edits) in enumerate(PROBES):
            copy = Path(temp) / f'probe-{index}'
            shutil.copytree(HERE, copy)
            mutate(copy, edits)
            try:
                validator.validate(repo, copy, emit=False)
            except ValueError as error:
                if expected not in str(error):
                    raise AssertionError(f'{name}: wrong rejection: {error}') from error
            else:
                raise AssertionError(f'{name}: malformed fixture passed')
            results.append({'probe': name, 'result': 'REJECTED', 'reason': expected})
    print(json.dumps({'status': 'PASS', 'additional_negative_probes': len(results), 'results': results, 'canonical_package': 'unchanged'}, indent=2))


if __name__ == '__main__':
    main()
