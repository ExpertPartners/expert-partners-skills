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
    ('review-receipt claims PR merged', 'review-receipt claims PR merged or closed', [
        ('set', 'review-receipt.json', ('review_pr', 'state'), 'MERGED'),
    ]),
    ('review-receipt claims auto-merge armed', 'review-receipt claims auto-merge armed', [
        ('set', 'review-receipt.json', ('review_pr', 'autoMergeRequest'), {'enabledAt': 'now'}),
    ]),
    ('source-manifest rubric delivery claim', 'source-manifest required_inputs disagree with pins', [
        ('set', 'source-manifest.json', ('required_inputs', 6, 'candidate_delivery'), 'deliver rubric to candidate'),
    ]),
    ('source-manifest disagrees with pins', 'source-manifest required_inputs disagree with pins', [
        ('set', 'source-manifest.json', ('required_inputs', 0, 'sha256'), '0' * 64),
    ]),
    ('review-receipt continuation result claim', 'review-receipt continuation result claim changed', [
        ('set', 'review-receipt.json', ('independent_continuation_retrieval', 'result'), 'Gate A PASS'),
    ]),
    ('review-receipt remote-readback result claim', 'review-receipt remote-readback result claim changed', [
        ('set', 'review-receipt.json', ('remote_readback', 'result'), 'qualification complete'),
    ]),
    ('extra nested hosted-check result field', 'review-receipt check entry schema drift', [
        ('set', 'review-receipt.json', ('review_pr', 'statusCheckRollup', 0, 'gate_a_status'), 'PASS'),
        ('refresh_manifest', 'artifact-manifest.json', (), 'review-receipt.json'),
    ]),
    ('missing nested hosted-check field', 'review-receipt check entry schema drift', [
        ('remove', 'review-receipt.json', ('review_pr', 'statusCheckRollup', 0, 'detailsUrl'), None),
        ('refresh_manifest', 'artifact-manifest.json', (), 'review-receipt.json'),
    ]),
    ('forged successful Gate A hosted check', 'review-receipt check rollup changed', [
        ('append_check', 'review-receipt.json', (), None),
        ('refresh_manifest', 'artifact-manifest.json', (), 'review-receipt.json'),
    ]),
    ('zero remote-readback count', 'review-receipt remote-readback count changed', [
        ('set', 'review-receipt.json', ('remote_readback', 'artifact_hashes_checked'), 0),
        ('refresh_manifest', 'artifact-manifest.json', (), 'review-receipt.json'),
    ]),
    ('removed source-review records', 'source-review record set changed', [
        ('set_root', 'source-review-comments.json', (), []),
        ('refresh_manifest', 'artifact-manifest.json', (), 'source-review-comments.json'),
    ]),
    ('source-review body changed without digest', 'source-review body digest mismatch', [
        ('set', 'source-review-comments.json', (1, 'body'), 'Altered source finding body'),
        ('refresh_manifest', 'artifact-manifest.json', (), 'source-review-comments.json'),
    ]),
    ('source-review body and digest changed together', 'source-review captured records changed', [
        ('set', 'source-review-comments.json', (1, 'body'), 'Altered source finding body'),
        ('set', 'source-review-comments.json', (1, 'body_sha256'), validator.digest(b'Altered source finding body')),
        ('refresh_manifest', 'artifact-manifest.json', (), 'source-review-comments.json'),
    ]),
    ('proposal status and manifest changed together', 'source-review proposals changed', [
        ('replace_text', 'source-review-proposals.md', (), ('All three findings remain OPEN.', 'All three findings remain ACCEPTED.')),
        ('refresh_manifest', 'artifact-manifest.json', (), 'source-review-proposals.md'),
    ]),
    ('recorder handoff and manifest changed together', 'recorder-grader handoff changed', [
        ('replace_text', 'recorder-grader-handoff.md', (),
         ('Do not upload this package wholesale, grant directory access, send the rubric, attach coverage/expected behavior, include historical responses/grades, or include recorder/grader conversation history.',
          'Deliver the withheld rubric and coverage guidance to the candidate before every run.')),
        ('refresh_manifest', 'artifact-manifest.json', (), 'recorder-grader-handoff.md'),
    ]),
    ('withheld boundary and manifest changed together', 'withheld boundary instructions changed', [
        ('replace_text', 'withheld/README.md', (),
         ('Do not deliver this directory, the parent coverage files, the handoff, preparation reports, previous execution records, or prior answers to Scout.',
          'Deliver behavioral-rubric.snapshot.md and coverage files to Scout before each run.')),
        ('refresh_manifest', 'artifact-manifest.json', (), 'withheld/README.md'),
    ]),
    ('candidate wrapper and manifest changed together', 'candidate neutral wrapper changed', [
        ('replace_text', 'candidate/README.md', (),
         ('No prior candidate answers or grader feedback are included.',
          'Include withheld rubric hints and prior grader feedback in candidate inputs.')),
        ('refresh_manifest', 'artifact-manifest.json', (), 'candidate/README.md'),
    ]),
    ('review-receipt claims candidate runtime', 'review-receipt claims candidate runtime', [
        ('set', 'review-receipt.json', ('candidate_runtime',), 'PASS'),
    ]),
    ('source-manifest claims candidate execution', 'source-manifest claims candidate execution', [
        ('set', 'source-manifest.json', ('candidate_execution',), 'PASS'),
    ]),
    ('source-manifest erases effort mismatch', 'source-manifest captured facts changed', [
        ('set', 'source-manifest.json', ('runtime_observation', 'mismatch_disclosed'), False),
        ('refresh_manifest', 'artifact-manifest.json', (), 'source-manifest.json'),
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
        if action == 'refresh_manifest':
            manifest = validator.read_json(path)
            entry_path = validator.PACKAGE_PREFIX + value
            entries = [entry for entry in manifest['files'] if entry['path'] == entry_path]
            if len(entries) != 1:
                raise AssertionError(f'Expected one manifest entry for {value}')
            data = (package / value).read_bytes()
            entries[0]['sha256'] = validator.digest(data)
            entries[0]['bytes'] = len(data)
            path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
            continue
        if action == 'set_root':
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
            continue
        if action == 'append_check':
            document = validator.read_json(path)
            checks = document['review_pr']['statusCheckRollup']
            forged = dict(checks[0])
            forged.update({'name': 'Gate A qualification', 'conclusion': 'SUCCESS'})
            checks.append(forged)
            path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n')
            continue
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
        clone = Path(temp).resolve() / 'source-clone'
        subprocess.run(['git', 'clone', '--quiet', '--shared', '--no-checkout', str(repo), str(clone)], check=True)
        pins = validator.read_json(HERE / PINS)
        subprocess.run(['git', '-C', str(clone), 'checkout', pins['source_commit'], '--', *validator.REQUIRED], check=True)
        for relative in validator.EXTERNAL_MANIFEST_FILES:
            destination = clone / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repo / relative, destination)
        source = clone / validator.REQUIRED[0]
        outside = Path(temp).resolve() / 'identical-outside-source'
        outside.write_bytes(source.read_bytes())
        source.rename(Path(temp).resolve() / 'preserved-source')
        source.symlink_to(outside)
        copy = Path(temp) / 'symlink-source-package'
        shutil.copytree(HERE, copy)
        try:
            validator.validate(clone, copy.resolve(), emit=False)
        except ValueError as error:
            if 'checked-out source is not a regular file' not in str(error):
                raise AssertionError(f'symlinked pinned source: wrong rejection: {error}') from error
        else:
            raise AssertionError('symlinked pinned source: malformed fixture passed')
        results.append({'probe': 'symlinked pinned source file with matching bytes', 'result': 'REJECTED',
                        'reason': 'checked-out source is not a regular file'})
        source.unlink()
        (Path(temp).resolve() / 'preserved-source').rename(source)
        source_dir = clone / 'skills/repo-standards'
        outside_dir = Path(temp).resolve() / 'identical-external-source-tree'
        source_dir.rename(outside_dir)
        source_dir.symlink_to(outside_dir, target_is_directory=True)
        try:
            validator.validate(clone, copy.resolve(), emit=False)
        except ValueError as error:
            if 'checked-out source path is symlinked' not in str(error):
                raise AssertionError(f'symlinked pinned source ancestor: wrong rejection: {error}') from error
        else:
            raise AssertionError('symlinked pinned source ancestor: malformed fixture passed')
        results.append({'probe': 'symlinked pinned source ancestor with matching bytes', 'result': 'REJECTED',
                        'reason': 'checked-out source path is symlinked'})
        source_dir.unlink()
        outside_dir.rename(source_dir)
        alias = Path(temp).resolve() / 'repo-root-alias'
        alias.symlink_to(clone, target_is_directory=True)
        command = [sys.executable, '-B', str(HERE / 'validate-package.py'), '--repo', str(alias),
                   '--package', str(copy.resolve())]
        linked = subprocess.run(command, text=True, capture_output=True, check=False)
        if linked.returncode != 1 or 'repository missing or symlinked' not in linked.stderr:
            raise AssertionError(f'symlinked repository root: wrong result: {linked.returncode}: {linked.stderr}')
        results.append({'probe': 'symlinked repository root', 'result': 'REJECTED',
                        'reason': 'repository missing or symlinked'})
        external = clone / 'intake/2026-09-23-grok-qualification-setup.md'
        outside_artifact = Path(temp).resolve() / 'identical-external-artifact'
        external.rename(outside_artifact)
        external.symlink_to(outside_artifact)
        try:
            validator.validate(clone, copy.resolve(), emit=False)
        except ValueError as error:
            if 'external manifest target is not a regular file' not in str(error):
                raise AssertionError(f'symlinked external artifact: wrong rejection: {error}') from error
        else:
            raise AssertionError('symlinked external artifact: malformed fixture passed')
        results.append({'probe': 'symlinked external manifest artifact with matching bytes', 'result': 'REJECTED',
                        'reason': 'external manifest target is not a regular file'})
        external.unlink()
        outside_artifact.rename(external)
        external_parent = clone / 'intake'
        outside_parent = Path(temp).resolve() / 'identical-external-artifact-tree'
        external_parent.rename(outside_parent)
        external_parent.symlink_to(outside_parent, target_is_directory=True)
        try:
            validator.validate(clone, copy.resolve(), emit=False)
        except ValueError as error:
            if 'external manifest path is symlinked' not in str(error):
                raise AssertionError(f'symlinked external ancestor: wrong rejection: {error}') from error
        else:
            raise AssertionError('symlinked external ancestor: malformed fixture passed')
        results.append({'probe': 'symlinked external manifest ancestor with matching bytes', 'result': 'REJECTED',
                        'reason': 'external manifest path is symlinked'})
    final_files = {str(path.relative_to(HERE)): validator.digest(path.read_bytes())
                   for path in HERE.rglob('*') if path.is_file()}
    if final_files != initial_files:
        raise AssertionError('canonical package changed during regression run')
    print(json.dumps({'status': 'PASS', 'additional_negative_probes': len(results), 'results': results, 'canonical_package': 'unchanged'}, indent=2))


if __name__ == '__main__':
    main()
