#!/usr/bin/env python3
"""Read-only preparation checks. No candidate execution or qualification grading."""
import argparse
import hashlib
import json
import re
import shutil
import stat
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
SOURCE_PIN_FIELDS = {'status', 'repository', 'source_commit', 'hash_algorithm', 'inputs'}
CANDIDATE_PIN_FIELDS = SOURCE_PIN_FIELDS | {'ordinary_case_input_paths', 'grok_case_input_paths'}
PIN_FIELDS = {'path', 'commit', 'git_blob', 'sha256', 'bytes', 'source_url'}
COVERAGE_FIELDS = {'status', 'source_commit', 'counts', 'cases'}
COVERAGE_CASE_FIELDS = {'case_id', 'mode', 'request_sha256', 'run_ids', 'variants'}
COVERAGE_VARIANT_FIELDS = {'variant_id', 'scenario', 'required_runs'}
RECEIPT_FIELDS = {
    'status', 'execution_status', 'gate_a_status', 'source_commit',
    'planned_source_pins', 'counts', 'pre_run_release_checks',
    'repeat_comparison', 'case_run_files',
}
# SHA-256 of compact, key-sorted JSON [{"variant_id": ..., "scenario": ...}, ...]
# in canonical coverage order, reviewed at e848326. Never compute the expected
# value from the candidate package being checked.
SCENARIO_TEXT_SHA256 = '913762fdcf90d9b3faf1782c46eeee651a9367755d856ce04c7a7e717e818f9c'
RUN_NULL_FIELDS = {
    'candidate_actor', 'candidate_model', 'candidate_surface', 'native_bot_id', 'native_run_id', 'isolation_evidence_ref', 'standing_instructions_hash', 'delivered_input_manifest_ref', 'delivered_input_hash', 'exact_request_artifact_ref', 'exact_request_artifact_sha256', 'raw_response_ref', 'raw_response_sha256', 'native_action_trace_ref', 'native_action_trace_sha256', 'trace_completeness_evidence_ref', 'before_snapshot_ref', 'after_snapshot_ref', 'recorder_identity', 'recorded_at', 'grader_identity', 'grader_model', 'graded_at', 'prohibited_action_count', 'coverage_omissions', 'limitations',
}
VARIANT_NULL_FIELDS = {'native_run_ids', 'independence_evidence_ref', 'fixed_response_citations', 'rubric_observations', 'missing_required_findings', 'failure_or_omission', 'grade'}
SHARD_FIELDS = {'status', 'execution_status', 'group', 'run_number', 'case_runs'}
RUN_FIELDS = RUN_NULL_FIELDS | {'run_id', 'case_id', 'run_number', 'mode', 'planned_request_sha256', 'status', 'no_write_proof_status', 'variant_grades'}
VARIANT_FIELDS = VARIANT_NULL_FIELDS | {'variant_id', 'status'}
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
COVERAGE_MD_SHA256 = '3646b5ead333c322a4b57c279487f5819bd504166060073b122638bbf79a6e28'
PACKAGE_PREFIX = 'intake/2026-09-23-grok-qualification-setup/'
PACKAGE_FILES = {
    'candidate/README.md', 'candidate/case-modes.json',
    'candidate/requests.json', 'candidate/source-inputs.json',
    'coverage.json', 'coverage.md', 'lifecycle-handoff.md',
    'recorder-grader-handoff.md', 'review-receipt.json',
    'route-assessment.md', 'source-manifest.json',
    'source-review-comments.json', 'source-review-proposals.md',
    'test_validate_package.py', 'validate-package.py', 'validation.md',
    'withheld/README.md', 'withheld/behavioral-rubric.snapshot.md',
    'withheld/receipt-grok-run-1.json', 'withheld/receipt-grok-run-2.json',
    'withheld/receipt-ordinary-run-1.json',
    'withheld/receipt-ordinary-run-2.json',
    'withheld/receipt-template.json', 'withheld/source-pins.json',
}
EXTERNAL_MANIFEST_FILES = {
    'archive/session-grok-repo-templates-qualification-setup-closeout-2026-09-23.md',
    'intake/2026-09-23-grok-qualification-setup.md',
}
MANIFEST_FIELDS = {'status', 'meaning', 'source_commit', 'files'}
MANIFEST_FILE_FIELDS = {'path', 'sha256', 'bytes'}
REVIEW_RECEIPT_FIELDS = {
    'candidate_runtime',
    'captured_at',
    'independent_continuation_retrieval',
    'lifecycle',
    'publication',
    'remote_readback',
    'review_pr',
    'source_review_findings',
    'status',
}
SOURCE_MANIFEST_TOP_FIELDS = {
    'authority_note',
    'brief_sha256',
    'candidate_execution',
    'captured_at',
    'governance_and_context',
    'private_repositories',
    'remote_heads_at_capture',
    'required_inputs',
    'resolved_lookup_errors',
    'runtime_observation',
    'skills_base_commit',
    'status',
}
INDEPENDENT_CONTINUATION_FIELDS = {
    'head',
    'linked_sources',
    'minor_stale_wording',
    'reader',
    'result',
    'start',
}
REMOTE_READBACK_FIELDS = {
    'artifact_hashes_checked',
    'head',
    'result',
}
EXPECTED_INDEPENDENT_CONTINUATION_RESULT = 'PASS, 38 cases/72 variants/144 required observations, all unrun, no gate/archive pass claimed'
EXPECTED_REMOTE_READBACK_RESULT = 'PASS via independent GitHub contents reads'
EXPECTED_REVIEW_LIFECYCLE = 'Own-row write rejected by automatic approval review before execution; proposed row remains a review-only handoff.'
EXPECTED_REVIEW_PUBLICATION = 'Review branch only. Not authoritative-main publication. Merge and auto-merge not performed.'
EXPECTED_SOURCE_REVIEW_FINDINGS = 'All three OPEN'
EXPECTED_CANDIDATE_DELIVERY = (
    'mode-scoped only; see candidate inputs',
    'mode-scoped only; see candidate inputs',
    'mode-scoped only; see candidate inputs',
    'mode-scoped only; see candidate inputs',
    'mode-scoped only; see candidate inputs',
    'mode-scoped only; see candidate inputs',
    'withheld',
)
REVIEW_PR_FIELDS = {
    'autoMergeRequest',
    'baseRefOid',
    'headRefOid',
    'isDraft',
    'state',
    'statusCheckRollup',
    'url',
}
REVIEW_CHECK_FIELDS = {
    '__typename', 'completedAt', 'conclusion', 'detailsUrl',
    'name', 'startedAt', 'status', 'workflowName',
}
# Anchors from the unchanged historical capture at 384b153. The artifact
# manifest can be refreshed with an altered claim, so it is not the authority
# for these result-bearing records.
REVIEW_CHECKS_SHA256 = 'a99e99df0a5eaad34c222ac60fcab7cad810cab7c9d2e8fbb4e4e9fd49a9944b'
REVIEW_RECEIPT_SHA256 = 'f8653693cdf024f611bc509570787ab89c46dd1d1754bf282c8479011902e618'
SOURCE_REVIEW_COMMENTS_SHA256 = '6c74e6ba1193a57df13cfcf0b5ec197a91216a1e4a14ca090af3e354eac8cc62'
SOURCE_MANIFEST_SHA256 = '6097f31e99f5b06fa91d61e789c78cf97ff46a0204c1da3c161fcd5a894bf9be'
# Reviewed preparation boundaries, independent of the refreshable artifact manifest.
SOURCE_REVIEW_PROPOSALS_SHA256 = 'ed9ff93d86295dd6a809f29e6db0b7a74017b922272236ada5920e0d785ad1c7'
RECORDER_GRADER_HANDOFF_SHA256 = 'cc8efdd3446f4a2898b3b385c9d0cf1106bc8ca1ebe96533fee25326d26a3512'
WITHHELD_README_SHA256 = 'dc0b6201b8b8356bb6be51f95509d99a0720c45a825a42e720275fc55c517fe5'
SOURCE_REVIEW_COMMENT_FIELDS = {'id', 'html_url', 'created_at', 'updated_at', 'body', 'body_sha256'}
SOURCE_REVIEW_COMMENT_IDS = (5801594731, 4086060528, 4086060537, 4086060558)
SOURCE_MANIFEST_INPUT_FIELDS = {
    'blob',
    'bytes',
    'candidate_delivery',
    'commit',
    'path',
    'repo',
    'sha256',
    'url',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def require_exact_keys(value, expected, message):
    require(type(value) is dict and set(value) == expected, message)


def require_text(value, message):
    require(type(value) is str and bool(value), message)


def require_hex(value, length, message):
    require(type(value) is str and re.fullmatch(rf'[0-9a-f]{{{length}}}', value) is not None, message)


def require_counts(value, message):
    require_exact_keys(value, set(COUNTS), message)
    require(all(type(value[key]) is int for key in COUNTS), message)
    require(value == COUNTS, message)


def require_pin_fields(pin, message):
    require_exact_keys(pin, PIN_FIELDS, message)
    require_text(pin['path'], message)
    require_hex(pin['commit'], 40, message)
    require_hex(pin['git_blob'], 40, message)
    require_hex(pin['sha256'], 64, message)
    require(type(pin['bytes']) is int and pin['bytes'] >= 0, message)
    require_text(pin['source_url'], message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def record_digest(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())


def mode(case_id):
    if not case_id.startswith('grok-'):
        return 'parent-non-grok'
    return 'hypothetical-fixer' if case_id.startswith('grok-fixer-') else 'auditor'



def require_unaliased_dir(path, message):
    """Reject missing dirs and any symlink in the path or its ancestors."""
    require(path.exists() and path.is_dir(), message)
    cursor = path
    while True:
        require(not cursor.is_symlink(), message)
        parent = cursor.parent
        if parent == cursor:
            break
        cursor = parent


def read_json(path):
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique_keys)


def validate(repo, package, emit=True):
    require_unaliased_dir(repo, 'repository missing or symlinked')
    require_unaliased_dir(package, 'package missing or symlinked')
    for path in package.rglob('*'):
        require(not path.is_symlink(), f'symlink not allowed in preparation package: {path}')
    actual_files = {str(path.relative_to(package)) for path in package.rglob('*') if path.is_file()}
    require(actual_files == PACKAGE_FILES | {'artifact-manifest.json'}, 'preparation package file set changed')
    pins = read_json(package / 'withheld/source-pins.json')
    require_exact_keys(pins, SOURCE_PIN_FIELDS, 'source-pin top-level schema drift')
    require(pins['status'] == DRAFT, 'source pin release state changed')
    require(pins['repository'] == 'ExpertPartners/expert-partners-skills', 'wrong source repository')
    commit = pins['source_commit']
    require_hex(commit, 40, 'source must be an exact commit')
    require(pins['hash_algorithm'] == 'SHA-256', 'source pin algorithm changed')
    require(type(pins['inputs']) is list and len(pins['inputs']) == len(REQUIRED), 'source pin input list drift')
    for pin in pins['inputs']:
        require_pin_fields(pin, 'source-pin input schema or type drift')
    require([p['path'] for p in pins['inputs']] == REQUIRED, 'seven core inputs missing/reordered/replaced')
    source = {}
    for pin in pins['inputs']:
        path = pin['path']
        require(pin['commit'] == commit, f'inconsistent commit: {path}')
        data = subprocess.check_output(['git', '-C', str(repo), 'show', f'{commit}:{path}'])
        blob = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', f'{commit}:{path}'], text=True).strip()
        require(blob == pin['git_blob'], f'blob mismatch: {path}')
        require(digest(data) == pin['sha256'] and len(data) == pin['bytes'], f'source SHA/size mismatch: {path}')
        source_path = repo / path
        require_unaliased_dir(source_path.parent, f'checked-out source path is symlinked: {path}')
        require(stat.S_ISREG(source_path.lstat().st_mode), f'checked-out source is not a regular file: {path}')
        require(source_path.read_bytes() == data, f'current checked-out source drift: {path}')
        require(pin['source_url'] == f'https://github.com/ExpertPartners/expert-partners-skills/blob/{commit}/{path}', f'bad source pointer: {path}')
        source[path] = data
    candidate = package / 'candidate'
    require({str(p.relative_to(candidate)) for p in candidate.rglob('*')} == {'README.md', 'requests.json', 'source-inputs.json', 'case-modes.json'}, 'unexpected candidate material or nested directory')
    require((candidate / 'requests.json').read_bytes() == source[REQUIRED[5]], 'candidate canonical request bytes changed')
    require((package / 'withheld/behavioral-rubric.snapshot.md').read_bytes() == source[REQUIRED[6]], 'withheld canonical rubric bytes changed')
    candidate_pins = read_json(candidate / 'source-inputs.json')
    require_exact_keys(candidate_pins, CANDIDATE_PIN_FIELDS, 'candidate source-pin top-level schema drift')
    require(type(candidate_pins['inputs']) is list and len(candidate_pins['inputs']) == 6, 'candidate source-pin input list drift')
    for pin in candidate_pins['inputs']:
        require_pin_fields(pin, 'candidate source-pin input schema or type drift')
    require(type(candidate_pins['ordinary_case_input_paths']) is list and all(type(p) is str for p in candidate_pins['ordinary_case_input_paths']), 'candidate ordinary path type drift')
    require(type(candidate_pins['grok_case_input_paths']) is list and all(type(p) is str for p in candidate_pins['grok_case_input_paths']), 'candidate Grok path type drift')
    expected_pins = {
        'status': DRAFT,
        'repository': 'ExpertPartners/expert-partners-skills',
        'source_commit': commit,
        'hash_algorithm': 'SHA-256',
        'inputs': [{key: pin[key] for key in PIN_FIELDS} for pin in pins['inputs'][:6]],
        'ordinary_case_input_paths': REQUIRED[:3],
        'grok_case_input_paths': REQUIRED[:5],
    }
    require(candidate_pins == expected_pins, 'candidate source boundary changed or withheld input included')
    readme = (candidate / 'README.md').read_text()
    require(DRAFT in readme, 'candidate fixture missing draft label')
    require(digest(readme.encode()) == '49d16ec1e5f621e1dbfbcb34c0b854b850285ed4d468de11b0230ccd820d6a76', 'candidate neutral wrapper changed; review and repin required')
    cases = read_json(candidate / 'requests.json')
    require(type(cases) is list, 'candidate case list type drift')
    for case in cases:
        require_exact_keys(case, {'id', 'request'}, 'candidate case schema drift')
        require_text(case['id'], 'candidate case id type drift')
        require_text(case['request'], 'candidate request type drift')
    require(len(cases) == 38 and len({c['id'] for c in cases}) == 38, 'case set incomplete or duplicated')
    expected_modes = {'status': DRAFT, 'cases': [{'case_id': c['id'], 'mode': mode(c['id'])} for c in cases]}
    modes = read_json(candidate / 'case-modes.json')
    require_exact_keys(modes, {'status', 'cases'}, 'candidate mode-map schema drift')
    require(type(modes['cases']) is list, 'candidate mode-map case list type drift')
    for item in modes['cases']:
        require_exact_keys(item, {'case_id', 'mode'}, 'candidate mode-map case schema drift')
        require_text(item['case_id'], 'candidate mode-map id type drift')
        require_text(item['mode'], 'candidate mode-map value type drift')
    require(modes == expected_modes, 'mode distinction lost')
    matrix = read_json(package / 'coverage.json')
    require_exact_keys(matrix, COVERAGE_FIELDS, 'coverage top-level schema drift')
    require(matrix['status'] == DRAFT and matrix['source_commit'] == commit, 'coverage source/release mismatch')
    require_counts(matrix['counts'], 'coverage counts schema, type or value drift')
    require(type(matrix['cases']) is list, 'coverage case list type drift')
    for row in matrix['cases']:
        require_exact_keys(row, COVERAGE_CASE_FIELDS, 'coverage case schema drift')
        require_text(row['case_id'], 'coverage case id type drift')
        require_text(row['mode'], 'coverage mode type drift')
        require_hex(row['request_sha256'], 64, 'coverage request hash type drift')
        require(type(row['run_ids']) is list and all(type(value) is str for value in row['run_ids']), 'coverage run-id list type drift')
        require(type(row['variants']) is list, 'coverage variant list type drift')
        for variant in row['variants']:
            require_exact_keys(variant, COVERAGE_VARIANT_FIELDS, 'coverage variant schema drift')
            require_text(variant['variant_id'], 'coverage variant id type drift')
            require_text(variant['scenario'], 'coverage scenario type drift')
            require(type(variant['required_runs']) is list and all(type(value) is int for value in variant['required_runs']), 'coverage required-run type drift')
    require([c['case_id'] for c in matrix['cases']] == [c['id'] for c in cases], 'coverage case mismatch')
    expected_rows = {}
    for case, row in zip(cases, matrix['cases']):
        cid = case['id']
        ids = [f'{cid}/{v}' for v in VARIANTS.get(cid, ['scenario'])]
        require(row['mode'] == mode(cid), f'mode mismatch: {cid}')
        require(row['request_sha256'] == digest(case['request'].encode()), f'request hash mismatch: {cid}')
        require(row['run_ids'] == [f'{cid}/run-1', f'{cid}/run-2'], f'missing run: {cid}')
        require([v['variant_id'] for v in row['variants']] == ids, f'variant omission: {cid}')
        require(all(v['required_runs'] == [1, 2] for v in row['variants']), f'variant run coverage: {cid}')
        for n in (1, 2):
            expected_rows[f'{cid}/run-{n}'] = (cid, n, row['request_sha256'], ids)
    require(sum(len(v[3]) for v in expected_rows.values()) == 144, 'not all 144 variant judgments present')
    scenario_pairs = [{'variant_id': variant['variant_id'], 'scenario': variant['scenario']} for row in matrix['cases'] for variant in row['variants']]
    scenario_bytes = json.dumps(scenario_pairs, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    require(digest(scenario_bytes) == SCENARIO_TEXT_SHA256, 'coverage scenario descriptions changed')
    require(digest((package / 'coverage.md').read_bytes()) == COVERAGE_MD_SHA256, 'coverage markdown changed')
    require(digest((package / 'source-review-proposals.md').read_bytes()) == SOURCE_REVIEW_PROPOSALS_SHA256,
            'source-review proposals changed')
    require(digest((package / 'recorder-grader-handoff.md').read_bytes()) == RECORDER_GRADER_HANDOFF_SHA256,
            'recorder-grader handoff changed')
    require(digest((package / 'withheld/README.md').read_bytes()) == WITHHELD_README_SHA256,
            'withheld boundary instructions changed')
    receipt = read_json(package / 'withheld/receipt-template.json')
    require_exact_keys(receipt, RECEIPT_FIELDS, 'aggregate receipt top-level schema drift')
    require(receipt['status'] == DRAFT and receipt['execution_status'] == 'NOT RUN' and receipt['gate_a_status'] == 'UNPROVEN', 'blank receipt makes a result claim')
    require(receipt['source_commit'] == commit and receipt['planned_source_pins'] == 'source-pins.json', 'receipt pin mismatch')
    require_counts(receipt['counts'], 'receipt counts schema, type or value drift')
    require_exact_keys(receipt['pre_run_release_checks'], PRE_RUN_RELEASE_CHECK_FIELDS, 'pre-run release check schema drift')
    require_exact_keys(receipt['repeat_comparison'], REPEAT_COMPARISON_FIELDS, 'repeat comparison schema drift')
    require(all(v is None for v in receipt['pre_run_release_checks'].values()), 'release check falsely populated')
    require(receipt['repeat_comparison']['status'] == 'NOT RUN' and all(v is None for k, v in receipt['repeat_comparison'].items() if k != 'status'), 'repeat result falsely populated')
    expected_files = [f'receipt-{group}-run-{n}.json' for group in ('ordinary', 'grok') for n in (1, 2)]
    require(type(receipt['case_run_files']) is list and all(type(name) is str for name in receipt['case_run_files']), 'receipt shard list type drift')
    require(receipt['case_run_files'] == expected_files, 'receipt shard incomplete')
    rows = []
    for group in ('ordinary', 'grok'):
        group_ids = [case['id'] for case in cases if case['id'].startswith('grok-') == (group == 'grok')]
        for n in (1, 2):
            name = f'receipt-{group}-run-{n}.json'
            part = read_json(package / 'withheld' / name)
            require_exact_keys(part, SHARD_FIELDS, f'receipt shard schema drift: {name}')
            require(part['status'] == DRAFT and part['execution_status'] == 'NOT RUN', f'nonblank execution: {name}')
            require(part['group'] == group and type(part['group']) is str and part['run_number'] == n and type(part['run_number']) is int, f'receipt shard filename binding: {name}')
            require(type(part['case_runs']) is list and len(part['case_runs']) == len(group_ids), f'case shard list/count drift: {name}')
            for row in part['case_runs']:
                require_exact_keys(row, RUN_FIELDS, f'case-run schema drift: {name}')
                require_text(row['case_id'], f'case-run id type drift: {name}')
                require_text(row['run_id'], f'case-run run-id type drift: {name}')
                require(type(row['run_number']) is int, f'case-run number type drift: {name}')
                require_text(row['mode'], f'case-run mode type drift: {name}')
                require_hex(row['planned_request_sha256'], 64, f'case-run request hash type drift: {name}')
                require(type(row['variant_grades']) is list, f'case-run variant list type drift: {name}')
                require(row['run_number'] == n and row['run_id'] == f"{row['case_id']}/run-{n}", f'receipt shard row/filename binding: {name}')
            require([row['case_id'] for row in part['case_runs']] == group_ids, f'receipt shard case/filename binding: {name}')
            rows.extend(part['case_runs'])
    require(len(rows) == 76 and len({r['run_id'] for r in rows}) == 76, 'receipt case runs omitted or duplicated')
    for row in rows:
        require(row['run_id'] in expected_rows, 'extra case run')
        cid, n, request_hash, ids = expected_rows[row['run_id']]
        require(row['case_id'] == cid and row['run_number'] == n and row['mode'] == mode(cid) and row['planned_request_sha256'] == request_hash, f'run mismatch: {row["run_id"]}')
        require(row['status'] == 'NOT RUN' and row['no_write_proof_status'] == 'NOT RUN', 'fabricated execution status')
        require(all(row[k] is None for k in RUN_NULL_FIELDS), 'run evidence template not blank')
        for v in row['variant_grades']:
            require_exact_keys(v, VARIANT_FIELDS, 'variant result schema drift')
            require_text(v['variant_id'], 'variant result id type drift')
        require([v['variant_id'] for v in row['variant_grades']] == ids, 'variant grading cell missing')
        for v in row['variant_grades']:
            require(v['status'] == 'NOT RUN' and all(v[k] is None for k in VARIANT_NULL_FIELDS), 'variant result fabricated')
    for name in ['coverage.md', 'recorder-grader-handoff.md', 'withheld/README.md']:
        require(DRAFT in (package / name).read_text(), f'missing draft label: {name}')
    review_receipt = read_json(package / 'review-receipt.json')
    require_exact_keys(review_receipt, REVIEW_RECEIPT_FIELDS, 'review-receipt schema drift')
    require(review_receipt['status'] == DRAFT, 'review-receipt release state changed')
    require(review_receipt['candidate_runtime'] == 'NOT RUN', 'review-receipt claims candidate runtime')
    require_text(review_receipt['captured_at'], 'review-receipt captured_at type drift')
    require_exact_keys(review_receipt['review_pr'], REVIEW_PR_FIELDS, 'review-receipt review_pr schema drift')
    require(review_receipt['review_pr']['state'] == 'OPEN', 'review-receipt claims PR merged or closed')
    require(review_receipt['review_pr']['autoMergeRequest'] is None, 'review-receipt claims auto-merge armed')
    require(type(review_receipt['review_pr']['isDraft']) is bool, 'review-receipt review_pr isDraft type drift')
    require_text(review_receipt['review_pr']['url'], 'review-receipt review_pr url type drift')
    require_hex(review_receipt['review_pr']['baseRefOid'], 40, 'review-receipt review_pr baseRefOid type drift')
    require_hex(review_receipt['review_pr']['headRefOid'], 40, 'review-receipt review_pr headRefOid type drift')
    checks = review_receipt['review_pr']['statusCheckRollup']
    require(type(checks) is list and len(checks) == 8, 'review-receipt check rollup changed')
    for check in checks:
        require_exact_keys(check, REVIEW_CHECK_FIELDS, 'review-receipt check entry schema drift')
        require(check['__typename'] == 'CheckRun', 'review-receipt check entry type drift')
        for key in ('completedAt', 'detailsUrl', 'name', 'startedAt', 'status'):
            require_text(check[key], f'review-receipt check {key} type drift')
        require(type(check['conclusion']) is str and type(check['workflowName']) is str,
                'review-receipt check result type drift')
    require(record_digest(checks) == REVIEW_CHECKS_SHA256, 'review-receipt check rollup changed')
    require(review_receipt['lifecycle'] == EXPECTED_REVIEW_LIFECYCLE, 'review-receipt lifecycle claim changed')
    require(review_receipt['publication'] == EXPECTED_REVIEW_PUBLICATION, 'review-receipt publication claim changed')
    require(review_receipt['source_review_findings'] == EXPECTED_SOURCE_REVIEW_FINDINGS, 'review-receipt source-review claim changed')
    continuation = review_receipt['independent_continuation_retrieval']
    require_exact_keys(continuation, INDEPENDENT_CONTINUATION_FIELDS, 'review-receipt continuation schema drift')
    require(continuation['result'] == EXPECTED_INDEPENDENT_CONTINUATION_RESULT, 'review-receipt continuation result claim changed')
    require(type(continuation['linked_sources']) is list and all(type(v) is str for v in continuation['linked_sources']), 'review-receipt continuation sources type drift')
    readback = review_receipt['remote_readback']
    require_exact_keys(readback, REMOTE_READBACK_FIELDS, 'review-receipt remote-readback schema drift')
    require(readback['result'] == EXPECTED_REMOTE_READBACK_RESULT, 'review-receipt remote-readback result claim changed')
    require(type(readback['artifact_hashes_checked']) is int, 'review-receipt remote-readback count type drift')
    require(readback['artifact_hashes_checked'] == 24, 'review-receipt remote-readback count changed')
    require(record_digest(review_receipt) == REVIEW_RECEIPT_SHA256, 'review-receipt captured facts changed')
    source_manifest = read_json(package / 'source-manifest.json')
    require_exact_keys(source_manifest, SOURCE_MANIFEST_TOP_FIELDS, 'source-manifest schema drift')
    require(source_manifest['status'] == DRAFT, 'source-manifest release state changed')
    require(source_manifest['candidate_execution'] == 'NOT RUN', 'source-manifest claims candidate execution')
    require(source_manifest['skills_base_commit'] == commit, 'source-manifest base commit disagrees with pins')
    require(type(source_manifest['required_inputs']) is list and len(source_manifest['required_inputs']) == len(REQUIRED), 'source-manifest required_inputs list drift')
    for index, entry in enumerate(source_manifest['required_inputs']):
        require_exact_keys(entry, SOURCE_MANIFEST_INPUT_FIELDS, 'source-manifest required_inputs schema drift')
        pin = pins['inputs'][index]
        require(
            entry['repo'] == 'ExpertPartners/expert-partners-skills'
            and entry['path'] == pin['path']
            and entry['commit'] == pin['commit']
            and entry['blob'] == pin['git_blob']
            and entry['sha256'] == pin['sha256']
            and entry['bytes'] == pin['bytes']
            and entry['url'] == pin['source_url']
            and entry['candidate_delivery'] == EXPECTED_CANDIDATE_DELIVERY[index],
            f'source-manifest required_inputs disagree with pins: {pin["path"]}',
        )
    require(record_digest(source_manifest) == SOURCE_MANIFEST_SHA256,
            'source-manifest captured facts changed')
    source_comments = read_json(package / 'source-review-comments.json')
    require(type(source_comments) is list and len(source_comments) == len(SOURCE_REVIEW_COMMENT_IDS),
            'source-review record set changed')
    for record in source_comments:
        require_exact_keys(record, SOURCE_REVIEW_COMMENT_FIELDS, 'source-review record schema drift')
        require(type(record['id']) is int, 'source-review record id type drift')
        for key in ('html_url', 'created_at', 'updated_at', 'body'):
            require_text(record[key], f'source-review record {key} type drift')
        require_hex(record['body_sha256'], 64, 'source-review body digest type drift')
        require(digest(record['body'].encode()) == record['body_sha256'], 'source-review body digest mismatch')
    require(tuple(record['id'] for record in source_comments) == SOURCE_REVIEW_COMMENT_IDS,
            'source-review record set changed')
    require(record_digest(source_comments) == SOURCE_REVIEW_COMMENTS_SHA256,
            'source-review captured records changed')
    manifest = read_json(package / 'artifact-manifest.json')
    require_exact_keys(manifest, MANIFEST_FIELDS, 'artifact manifest schema drift')
    require(manifest['status'] == DRAFT and type(manifest['meaning']) is str and
            manifest['meaning'] == 'Prepared artifact bytes, no executed candidate results. This manifest excludes itself.' and
            manifest['source_commit'] == commit, 'artifact manifest identity changed')
    require(type(manifest['files']) is list, 'artifact manifest file list type drift')
    expected_manifest_paths = {PACKAGE_PREFIX + name for name in PACKAGE_FILES} | EXTERNAL_MANIFEST_FILES
    manifest_paths = []
    for entry in manifest['files']:
        require_exact_keys(entry, MANIFEST_FILE_FIELDS, 'artifact manifest entry schema drift')
        require(type(entry['path']) is str, 'artifact manifest path type drift')
        require_hex(entry['sha256'], 64, 'artifact manifest hash type drift')
        require(type(entry['bytes']) is int and entry['bytes'] >= 0, 'artifact manifest size type drift')
        manifest_paths.append(entry['path'])
    require(len(manifest_paths) == len(expected_manifest_paths) and
            set(manifest_paths) == expected_manifest_paths, 'artifact manifest file list changed')
    for entry in manifest['files']:
        relative = entry['path']
        target = package / relative.removeprefix(PACKAGE_PREFIX) if relative.startswith(PACKAGE_PREFIX) else repo / relative
        if relative in EXTERNAL_MANIFEST_FILES:
            require_unaliased_dir(target.parent, f'external manifest path is symlinked: {relative}')
            require(stat.S_ISREG(target.lstat().st_mode), f'external manifest target is not a regular file: {relative}')
        data = target.read_bytes()
        require(digest(data) == entry['sha256'] and len(data) == entry['bytes'],
                f'artifact manifest hash/size mismatch: {relative}')
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
            probe_package = probe_package.resolve()
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
    parser.add_argument('--package', type=Path, default=Path(__file__).absolute().parent, help='Package directory, default next to this script')
    parser.add_argument('--negative-probes', action='store_true', help='Check six schema mutations in temporary package copies')
    args = parser.parse_args()
    try:
        validate(args.repo.absolute(), args.package.absolute())
        if args.negative_probes:
            negative_probes(args.repo.absolute(), args.package.absolute())
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
