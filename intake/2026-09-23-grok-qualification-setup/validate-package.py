#!/usr/bin/env python3
"""Read-only preparation checks. No candidate execution or qualification grading."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED = [
    'skills/repo-standards/SKILL.md',
    'skills/repo-standards/references/content-architecture.md',
    'skills/repo-standards/references/audit-record-template.md',
    'skills/repo-standards/references/grok-auditor.md',
    'skills/repo-standards/references/grok-fixer.md',
    'skills/repo-standards/tests/behavioral-cases.json',
    'skills/repo-standards/tests/behavioral-rubric.md',
]
VARIANTS = {
    'digest-escalation': ['digest-qualification-omitted', 'digest-unavailable'],
    'grok-authority-signals': ['merged', 'canon-location', 'sole-index', 'metadata', 'newer-date', 'prettier-wording', 'greater-length', 'combined'],
    'grok-gates-and-cold-exam': ['proxy-a', 'finance-unaccepted', 'finance-merged', 'ab-accepted', 'north-absent'],
    'grok-bootstrap-drift': ['live-drift', 'live-unavailable'],
    'grok-fixer-admission': ['audit-absent', 'proof-incomplete', 'generic-trust', 'scope-absent', 'collision-stale', 'pr-overlap', 'collision-unavailable', 'shared-main', 'auth-unverified', 'revision-drift', 'authority-conflict'],
    'grok-fixer-forbidden': ['merge', 'auto-merge', 'delete-history', 'create-repository', 'permissions', 'governance', 'oauth', 'research-promotion', 'unrelated-defect', 'shared-ops'],
    'grok-fixer-positive': ['approved-typo', 'base-drift', 'unrelated-test-finding'],
}
COUNTS = {'cases': 38, 'ordinary_cases': 19, 'grok_cases': 19, 'scored_variants': 72, 'runs_per_case_and_variant': 2, 'full_case_receipt_slots': 76, 'variant_run_judgments': 144}
RUN_NULL_FIELDS = {
    'candidate_actor', 'candidate_model', 'candidate_surface', 'native_bot_id', 'native_run_id', 'isolation_evidence_ref', 'standing_instructions_hash', 'delivered_input_manifest_ref', 'delivered_input_hash', 'exact_request_artifact_ref', 'exact_request_artifact_sha256', 'raw_response_ref', 'raw_response_sha256', 'native_action_trace_ref', 'native_action_trace_sha256', 'trace_completeness_evidence_ref', 'before_snapshot_ref', 'after_snapshot_ref', 'recorder_identity', 'recorded_at', 'grader_identity', 'grader_model', 'graded_at', 'prohibited_action_count', 'coverage_omissions', 'limitations',
}
VARIANT_NULL_FIELDS = {'native_run_ids', 'independence_evidence_ref', 'fixed_response_citations', 'rubric_observations', 'missing_required_findings', 'failure_or_omission', 'grade'}
SHARD_FIELDS = {'status', 'execution_status', 'group', 'run_number', 'case_runs'}
PRE_RUN_RELEASE_CHECK_FIELDS = {
    'source_review_hold_resolved', 'north_test_authorization',
    'candidate_bot_identity_and_model_verified', 'independence_demonstrated',
    'fixed_input_delivery_verified', 'candidate_recorder_grader_separation_verified',
    'complete_independent_action_trace_available',
    'candidate_prerequisite_exposure_reviewed', 'no_held_exam_target_exposure_verified',
}
REPEAT_COMPARISON_FIELDS = {
    'status', 'same_input_evidence_ref', 'same_safety_decisions_all_required_findings',
    'failures_and_omissions', 'independent_grader_conclusion', 'acceptance_record_ref',
}
DRAFT = 'DRAFT / NOT RELEASED'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def require_exact_keys(value, expected, message):
    require(isinstance(value, dict) and set(value) == expected, message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def mode(case_id):
    if not case_id.startswith('grok-'):
        return 'parent-non-grok'
    return 'hypothetical-fixer' if case_id.startswith('grok-fixer-') else 'auditor'


def read_json(path):
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique_keys)


def validate(repo, package, emit=True):
    require(package.is_dir() and not package.is_symlink(), 'package missing or symlinked')
    for path in package.rglob('*'):
        require(not path.is_symlink(), f'symlink not allowed in preparation package: {path}')
    pins = read_json(package / 'withheld/source-pins.json')
    require(pins['status'] == DRAFT, 'source pin release state changed')
    require(pins['repository'] == 'ExpertPartners/expert-partners-skills', 'wrong source repository')
    commit = pins['source_commit']
    require(re.fullmatch(r'[0-9a-f]{40}', commit) is not None, 'source must be an exact commit')
    require([p['path'] for p in pins['inputs']] == REQUIRED, 'seven core inputs missing/reordered/replaced')
    source = {}
    for pin in pins['inputs']:
        path = pin['path']
        require(pin['commit'] == commit, f'inconsistent commit: {path}')
        data = subprocess.check_output(['git', '-C', str(repo), 'show', f'{commit}:{path}'])
        blob = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', f'{commit}:{path}'], text=True).strip()
        require(blob == pin['git_blob'], f'blob mismatch: {path}')
        require(digest(data) == pin['sha256'] and len(data) == pin['bytes'], f'source SHA/size mismatch: {path}')
        require((repo / path).read_bytes() == data, f'current checked-out source drift: {path}')
        require(pin['source_url'] == f'https://github.com/ExpertPartners/expert-partners-skills/blob/{commit}/{path}', f'bad source pointer: {path}')
        source[path] = data
    candidate = package / 'candidate'
    require({str(p.relative_to(candidate)) for p in candidate.rglob('*')} == {'README.md', 'requests.json', 'source-inputs.json', 'case-modes.json'}, 'unexpected candidate material or nested directory')
    require((candidate / 'requests.json').read_bytes() == source[REQUIRED[5]], 'candidate canonical request bytes changed')
    require((package / 'withheld/behavioral-rubric.snapshot.md').read_bytes() == source[REQUIRED[6]], 'withheld canonical rubric bytes changed')
    candidate_pins = read_json(candidate / 'source-inputs.json')
    expected_pins = {k: v for k, v in pins.items() if k != 'inputs'}
    expected_pins.update({'inputs': pins['inputs'][:6], 'ordinary_case_input_paths': REQUIRED[:3], 'grok_case_input_paths': REQUIRED[:5]})
    require(candidate_pins == expected_pins, 'candidate source boundary changed or withheld input included')
    readme = (candidate / 'README.md').read_text()
    require(DRAFT in readme, 'candidate fixture missing draft label')
    require(digest(readme.encode()) == '49d16ec1e5f621e1dbfbcb34c0b854b850285ed4d468de11b0230ccd820d6a76', 'candidate neutral wrapper changed; review and repin required')
    cases = read_json(candidate / 'requests.json')
    require(len(cases) == 38 and len({c['id'] for c in cases}) == 38, 'case set incomplete or duplicated')
    require(all(set(c) == {'id', 'request'} for c in cases), 'candidate case includes additional coaching or result fields')
    expected_modes = {'status': DRAFT, 'cases': [{'case_id': c['id'], 'mode': mode(c['id'])} for c in cases]}
    require(read_json(candidate / 'case-modes.json') == expected_modes, 'mode distinction lost')
    matrix = read_json(package / 'coverage.json')
    require(matrix['status'] == DRAFT and matrix['source_commit'] == commit, 'coverage source/release mismatch')
    require(matrix['counts'] == COUNTS, 'coverage counts changed')
    require([c['case_id'] for c in matrix['cases']] == [c['id'] for c in cases], 'coverage case mismatch')
    expected_rows = {}
    for case, row in zip(cases, matrix['cases']):
        cid = case['id']
        ids = [f'{cid}/{v}' for v in VARIANTS.get(cid, ['scenario'])]
        require(row['mode'] == mode(cid), f'mode mismatch: {cid}')
        require(row['request_sha256'] == digest(case['request'].encode()), f'request hash mismatch: {cid}')
        require(row['run_ids'] == [f'{cid}/run-1', f'{cid}/run-2'], f'missing run: {cid}')
        require([v['variant_id'] for v in row['variants']] == ids, f'variant omission: {cid}')
        require(all(v['required_runs'] == [1, 2] and v['scenario'] for v in row['variants']), f'variant run coverage: {cid}')
        for n in (1, 2):
            expected_rows[f'{cid}/run-{n}'] = (cid, n, row['request_sha256'], ids)
    require(sum(len(v[3]) for v in expected_rows.values()) == 144, 'not all 144 variant judgments present')
    receipt = read_json(package / 'withheld/receipt-template.json')
    require(receipt['status'] == DRAFT and receipt['execution_status'] == 'NOT RUN' and receipt['gate_a_status'] == 'UNPROVEN', 'blank receipt makes a result claim')
    require(receipt['source_commit'] == commit and receipt['planned_source_pins'] == 'source-pins.json', 'receipt pin mismatch')
    require(receipt['counts'] == COUNTS, 'receipt counts mismatch')
    require_exact_keys(receipt['pre_run_release_checks'], PRE_RUN_RELEASE_CHECK_FIELDS, 'pre-run release check schema drift')
    require_exact_keys(receipt['repeat_comparison'], REPEAT_COMPARISON_FIELDS, 'repeat comparison schema drift')
    require(all(v is None for v in receipt['pre_run_release_checks'].values()), 'release check falsely populated')
    require(receipt['repeat_comparison']['status'] == 'NOT RUN' and all(v is None for k, v in receipt['repeat_comparison'].items() if k != 'status'), 'repeat result falsely populated')
    expected_files = [f'receipt-{group}-run-{n}.json' for group in ('ordinary', 'grok') for n in (1, 2)]
    require(receipt['case_run_files'] == expected_files, 'receipt shard incomplete')
    rows = []
    for name in expected_files:
        part = read_json(package / 'withheld' / name)
        require_exact_keys(part, SHARD_FIELDS, f'receipt shard schema drift: {name}')
        require(part['status'] == DRAFT and part['execution_status'] == 'NOT RUN', f'nonblank execution: {name}')
        require(len(part['case_runs']) == 19, f'case shard incomplete: {name}')
        for row in part['case_runs']:
            require(row['run_number'] == part['run_number'], f'wrong run in {name}')
            require(row['case_id'].startswith('grok-') == (part['group'] == 'grok'), f'wrong mode group: {name}')
        rows.extend(part['case_runs'])
    require(len(rows) == 76 and len({r['run_id'] for r in rows}) == 76, 'receipt case runs omitted or duplicated')
    for row in rows:
        require(row['run_id'] in expected_rows, 'extra case run')
        cid, n, request_hash, ids = expected_rows[row['run_id']]
        require(row['case_id'] == cid and row['run_number'] == n and row['mode'] == mode(cid) and row['planned_request_sha256'] == request_hash, f'run mismatch: {row["run_id"]}')
        require(row['status'] == 'NOT RUN' and row['no_write_proof_status'] == 'NOT RUN', 'fabricated execution status')
        expected_fields = RUN_NULL_FIELDS | {'run_id', 'case_id', 'run_number', 'mode', 'planned_request_sha256', 'status', 'no_write_proof_status', 'variant_grades'}
        require(set(row) == expected_fields and all(row[k] is None for k in RUN_NULL_FIELDS), 'run evidence template not blank or schema drift')
        require([v['variant_id'] for v in row['variant_grades']] == ids, 'variant grading cell missing')
        for v in row['variant_grades']:
            require(set(v) == VARIANT_NULL_FIELDS | {'variant_id', 'status'} and v['status'] == 'NOT RUN' and all(v[k] is None for k in VARIANT_NULL_FIELDS), 'variant result fabricated or schema drift')
    for name in ['coverage.md', 'recorder-grader-handoff.md', 'withheld/README.md']:
        require(DRAFT in (package / name).read_text(), f'missing draft label: {name}')
    if emit:
        print(json.dumps({'status': 'PASS', 'meaning': 'preparation consistency only; no candidate run or qualification', 'source_commit': commit, 'core_input_hashes_verified': 7, **COUNTS}, indent=2))


def negative_probes(repo, package):
    probes = [
        ('extra shard result field', 'withheld/receipt-grok-run-1.json', 'add', 'gate_a_status', 'PASS', 'receipt shard schema drift'),
        ('missing shard field', 'withheld/receipt-grok-run-1.json', 'remove', 'group', None, 'receipt shard schema drift'),
        ('extra pre-run check key', 'withheld/receipt-template.json', 'add', 'unexpected_release_check', None, 'pre-run release check schema drift'),
        ('missing pre-run check key', 'withheld/receipt-template.json', 'remove', 'no_held_exam_target_exposure_verified', None, 'pre-run release check schema drift'),
        ('extra repeat comparison key', 'withheld/receipt-template.json', 'add', 'unexpected_comparison', None, 'repeat comparison schema drift'),
        ('missing repeat comparison key', 'withheld/receipt-template.json', 'remove', 'same_input_evidence_ref', None, 'repeat comparison schema drift'),
    ]
    results = []
    with tempfile.TemporaryDirectory(prefix='grok-qualification-probes-') as temp:
        for index, (name, relative, action, key, value, expected_error) in enumerate(probes):
            probe_package = Path(temp) / f'probe-{index}'
            shutil.copytree(package, probe_package)
            target = probe_package / relative
            document = read_json(target)
            mutated = document
            if relative == 'withheld/receipt-template.json':
                field = 'pre_run_release_checks' if 'pre-run' in name else 'repeat_comparison'
                mutated = document[field]
            if action == 'add':
                mutated[key] = value
            else:
                mutated.pop(key)
            target.write_text(json.dumps(document, indent=2) + '\n')
            try:
                validate(repo, probe_package, emit=False)
            except ValueError as exc:
                require(expected_error in str(exc), f'{name}: rejected for the wrong reason: {exc}')
            else:
                raise ValueError(f'{name}: mutation incorrectly passed validation')
            results.append({'probe': name, 'result': 'REJECTED', 'reason': expected_error})
    print(json.dumps({'negative_probes': results, 'result': 'PASS', 'canonical_package': 'unchanged'}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True, help='Existing verified source checkout; reads only')
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parent, help='Package directory, default next to this script')
    parser.add_argument('--negative-probes', action='store_true', help='Check six schema mutations in temporary package copies')
    args = parser.parse_args()
    try:
        validate(args.repo.resolve(), args.package.resolve())
        if args.negative_probes:
            negative_probes(args.repo.resolve(), args.package.resolve())
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
