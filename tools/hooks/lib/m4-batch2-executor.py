#!/usr/bin/env python3
"""Finite M4 transaction executor. Never called by passive PreToolUse evaluation.

Production paths and dispatch capability are fixed in main(). Tests import the
classes and supply a synthetic store/runtime; the CLI has no injection surface.
An action claim is permanent, including after a crash or uncertain child result.
"""

import contextlib
import fcntl
import hashlib
import hmac
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import time


POLICY_PATH = Path('/Users/allisongaddy/HQ-AI-Workspace-M4/Workbench/scripts/policies/m4-batch2-20260923.json')
POLICY_SHA256 = 'c567b56e56aad04bcfcbf10ff416906be12427709b80a9740fe5553dc55b96b9'
RUNTIME_PATH = Path('/Users/allisongaddy/HQ-AI-Workspace-M4/Workbench/scripts/lib/m4-batch2-runtime.py')
EXECUTOR_PATH = Path('/Users/allisongaddy/HQ-AI-Workspace-M4/Workbench/scripts/lib/m4-batch2-executor.py')
STATE_DIR = Path('/Users/allisongaddy/.claude/deletion-approvals/m4-batch2-20260923')
TTL_SECONDS = 900
MAX_RECORD_BYTES = 16 * 1024 * 1024
MAX_AUDIT_BYTES = 64 * 1024 * 1024
PROTECTED_KEYS = frozenset(('6583fba12287d067', '9833c18b2d85bc59'))
ALLOWED_KEYS = frozenset((
    '3fac9f70aa5c9ccf', '03676be6c5876144', '67eb4586ca667318',
    '705bc6b22212b352', '9eac9498388ae25e', '96a8727b140d6939',
    'bce731a0395adf49', 'cc2145a2fe1558fa', '7f312557c12f11a3',
    '3f410cde517faec3', 'a3586cc356aa4ace', '1ce9283feb7d83f2',
    '8003d8991b0d346b', '33664ddc0e10cefa', 'dcf0514efa8ecddd',
    '1bf7c3c15bf47d04', 'bd03aaf280724e38', 'f19f78a55038d137',
    '69f9afb961c37556', '705d23756ff7dacc', 'ffe2131771d88588',
    '1ddbeaccabfe00a4', '32026684e21afda6', '1a3c4333f3a90708',
    '67a0730928194b24', 'e41f203b7505f1fb', 'ac0ed6aa23b37c1e',
    '9dc43daea2065b57',
))


class GuardError(Exception):
    """A failure that must not confer dispatch authority."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise GuardError('duplicate JSON field')
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              GuardError('nonfinite JSON number')))
    except (ValueError, UnicodeError) as exc:
        raise GuardError('invalid JSON') from exc


def validate_action(action):
    if not isinstance(action, str):
        raise GuardError('action must be a string')
    if action == 'snapshot:131322':
        return action
    if re.fullmatch(r'npx:[0-9a-f]{16}', action) and action[4:] in ALLOWED_KEYS:
        return action
    raise GuardError('unlisted or malformed action')


def validate_replacement(action, replacement):
    if action.startswith('npx:'):
        if replacement is not None:
            raise GuardError('npx actions cannot bind a replacement snapshot')
    elif (not isinstance(replacement, str) or not re.fullmatch(
            r'[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}', replacement)):
        raise GuardError('snapshot grant requires a canonical replacement UUID')


class SecureStore:
    """Owned, private, no-follow files addressed relative to a locked directory.

    Files are append-only or exclusively created. No approval, claim, outcome,
    or audit record is unlinked, replaced, relaxed, or silently repaired.
    """

    def __init__(self, path, uid=None):
        self.path = Path(path)
        self.uid = os.getuid() if uid is None else uid
        if not self.path.is_absolute() or '..' in self.path.parts:
            raise GuardError('store path must be absolute without traversal')
        self._root_fd = None

    @staticmethod
    def note_name(action):
        return 'note-' + validate_action(action).replace(':', '-') + '.json'

    @staticmethod
    def claim_name(action):
        return 'claim-' + validate_action(action).replace(':', '-') + '.json'

    @staticmethod
    def outcome_name(action):
        return 'outcome-' + validate_action(action).replace(':', '-') + '.json'

    def _name(self, name):
        if not isinstance(name, str) or not re.fullmatch(r'[a-z0-9.-]+', name) or name in ('.', '..'):
            raise GuardError('invalid store filename')
        if self._root_fd is None:
            raise GuardError('store operation requires its transaction lock')

    def _check_file(self, fd):
        s = os.fstat(fd)
        if (not stat.S_ISREG(s.st_mode) or s.st_uid != self.uid or
                stat.S_IMODE(s.st_mode) != 0o600 or s.st_nlink != 1):
            raise GuardError('unsafe state-file type, owner, mode or hardlink count')
        return s

    def _open_directory(self, create):
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            parts = self.path.parts[1:]
            for index, part in enumerate(parts):
                try:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                except FileNotFoundError:
                    if not create:
                        raise GuardError('approval store does not exist')
                    os.mkdir(part, 0o700, dir_fd=fd)
                    os.fsync(fd)
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                s = os.fstat(child)
                final = index == len(parts) - 1
                sticky_root_temp = s.st_uid == 0 and bool(s.st_mode & stat.S_ISVTX)
                bad = (s.st_uid not in (0, self.uid) or
                       bool(stat.S_IMODE(s.st_mode) & 0o022) and not sticky_root_temp)
                if final:
                    bad = s.st_uid != self.uid or stat.S_IMODE(s.st_mode) != 0o700
                if bad:
                    os.close(child)
                    raise GuardError('unsafe state directory ownership or permissions')
                os.close(fd)
                fd = child
            return fd
        except BaseException:
            os.close(fd)
            raise

    @contextlib.contextmanager
    def lock(self, create=True):
        if self._root_fd is not None:
            raise GuardError('nested transaction lock')
        root = self._open_directory(create)
        lockfd = None
        self._root_fd = root
        try:
            flags = os.O_RDWR | os.O_NOFOLLOW
            if create:
                flags |= os.O_CREAT
            lockfd = os.open('transaction.lock', flags, 0o600, dir_fd=root)
            self._check_file(lockfd)
            fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.fsync(lockfd)
            os.fsync(root)
            yield self
        except OSError as exc:
            raise GuardError('secure store or exclusive transaction lock failed') from exc
        finally:
            self._root_fd = None
            if lockfd is not None:
                os.close(lockfd)
            os.close(root)

    def exists(self, name):
        self._name(name)
        try:
            s = os.stat(name, dir_fd=self._root_fd, follow_symlinks=False)
        except FileNotFoundError:
            return False
        if (not stat.S_ISREG(s.st_mode) or s.st_uid != self.uid or
                stat.S_IMODE(s.st_mode) != 0o600 or s.st_nlink != 1):
            raise GuardError('unsafe existing state file')
        return True

    def _read_raw(self, name, limit):
        self._name(name)
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self._root_fd)
        try:
            s = self._check_file(fd)
            if s.st_size > limit:
                raise GuardError('state file exceeds bound')
            chunks = []
            remaining = limit + 1
            while remaining:
                chunk = os.read(fd, min(65536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b''.join(chunks)
            if len(raw) > limit:
                raise GuardError('state file exceeds bound')
            return raw
        finally:
            os.close(fd)

    def read(self, name):
        return strict_json(self._read_raw(name, MAX_RECORD_BYTES))

    @staticmethod
    def _write_all(fd, raw):
        while raw:
            written = os.write(fd, raw)
            if written <= 0:
                raise GuardError('short state write')
            raw = raw[written:]

    def create(self, name, value):
        self._name(name)
        raw = canonical(value) + b'\n'
        if len(raw) > MAX_RECORD_BYTES:
            raise GuardError('record exceeds bound')
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=self._root_fd)
        try:
            self._check_file(fd)
            self._write_all(fd, raw)
            os.fsync(fd)
            os.fsync(self._root_fd)
        finally:
            os.close(fd)

    def audit_records(self):
        if not self.exists('audit.jsonl'):
            return []
        raw = self._read_raw('audit.jsonl', MAX_AUDIT_BYTES)
        if raw and not raw.endswith(b'\n'):
            raise GuardError('incomplete audit record')
        records, previous = [], '0' * 64
        for index, line in enumerate(raw.splitlines(), 1):
            record = strict_json(line)
            if not isinstance(record, dict) or set(record) != {'sequence', 'previous', 'event', 'payload', 'sha256'}:
                raise GuardError('invalid audit schema')
            body = {k: v for k, v in record.items() if k != 'sha256'}
            if (record['sequence'] != index or record['previous'] != previous or
                    not hmac.compare_digest(str(record['sha256']), digest(body))):
                raise GuardError('audit integrity failure')
            records.append(record)
            previous = record['sha256']
        return records

    def append_audit(self, event, payload):
        records = self.audit_records()
        record = {'sequence': len(records) + 1,
                  'previous': records[-1]['sha256'] if records else '0' * 64,
                  'event': event, 'payload': payload}
        record['sha256'] = digest(record)
        raw = canonical(record) + b'\n'
        fd = os.open('audit.jsonl', os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW,
                     0o600, dir_fd=self._root_fd)
        try:
            s = self._check_file(fd)
            if s.st_size + len(raw) > MAX_AUDIT_BYTES:
                raise GuardError('audit exceeds bound')
            self._write_all(fd, raw)
            os.fsync(fd)
            os.fsync(self._root_fd)
        finally:
            os.close(fd)
        return record


class Executor:
    def __init__(self, policy, runtime, store, policy_digest, clock=time.time, argv_resolver=None):
        if (not isinstance(policy, dict) or set(policy.get('npx_keys', [])) != ALLOWED_KEYS or
                len(policy.get('npx_keys', [])) != 28 or
                set(policy.get('active_keys', [])) != PROTECTED_KEYS):
            raise GuardError('finite action registry mismatch')
        if not re.fullmatch(r'[a-f0-9]{64}', str(policy_digest)):
            raise GuardError('invalid registry digest')
        if not isinstance(policy.get('task_id'), str) or not policy['task_id']:
            raise GuardError('missing task identity')
        if not re.fullmatch(r'[a-f0-9]{64}', str(policy.get('approval_sha256'))):
            raise GuardError('missing approval digest')
        self.policy, self.runtime, self.store = policy, runtime, store
        self.policy_digest, self.clock = policy_digest, clock
        self.argv_resolver = argv_resolver or runtime.fixed_argv

    def _context(self, action):
        validate_action(action)
        self.runtime.context_check()
        argv = self.argv_resolver(action)
        if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or '\x00' in x for x in argv):
            raise GuardError('invalid fixed argv')
        return argv

    def _now(self):
        now = self.clock()
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now) or now <= 0:
            raise GuardError('invalid clock')
        return now

    def _unused(self, action):
        if self.store.exists(self.store.claim_name(action)) or self.store.exists(self.store.outcome_name(action)):
            raise GuardError('action already claimed or closed; replay/regrant prohibited')

    def _outcomes(self, action):
        if action != 'snapshot:131322':
            return None
        audit = self.store.audit_records()
        receipts = []
        for key in self.policy['npx_keys']:
            name = self.store.outcome_name('npx:' + key)
            if not self.store.exists(name):
                raise GuardError('snapshot requires all 28 outcome receipts')
            outcome = self.store.read(name)
            if (not isinstance(outcome, dict) or outcome.get('action') != 'npx:' + key or
                    outcome.get('task_id') != self.policy['task_id'] or
                    outcome.get('policy_sha256') != self.policy_digest or
                    outcome.get('status') not in ('VERIFIED', 'SKIPPED')):
                raise GuardError('snapshot has incomplete/failed/corrupt outcome')
            if not any(r['event'] == 'TERMINAL' and r['payload'].get('outcome_sha256') == digest(outcome)
                       and r['payload'].get('action') == outcome['action'] for r in audit):
                raise GuardError('outcome has no durable terminal audit')
            claimed = self.store.exists(self.store.claim_name(outcome['action']))
            if claimed != (outcome['status'] == 'VERIFIED'):
                raise GuardError('outcome and permanent claim disagree')
            receipts.append(outcome)
        return receipts

    def preview(self, action):
        argv = self._context(action)
        return {'status': 'PREVIEW', 'action': action, 'argv': argv,
                'identity': self.runtime.identity(action), 'consumes_note': False,
                'binding_required': action == 'snapshot:131322'}

    def _blocked(self, action, stage, exc):
        # A system-wide safety refusal is never an eligible target skip.
        self.store.append_audit('BLOCKED', {'action': action, 'stage': stage,
            'task_id': self.policy['task_id'], 'policy_sha256': self.policy_digest,
            'reason': str(exc), 'recorded_epoch': self._now()})
        raise GuardError(stage + ' blocked: ' + str(exc)) from exc

    def _skip(self, action, reason, observation, authorization):
        # Only the runtime can supply a freshly and safely observed fixed target.
        # No note or deletion claim is created for this retained identity.
        if not action.startswith('npx:') or not isinstance(observation, dict) or not reason:
            raise GuardError('invalid target-specific skip evidence')
        self.runtime.context_check()
        fresh = self.runtime.target_observation(action)
        if fresh != observation:
            raise GuardError('target changed during skip observation')
        self.store.append_audit('SKIP_PREPARED', {'action': action,
            'task_id': self.policy['task_id'], 'policy_sha256': self.policy_digest,
            'reason': reason, 'skip_observation': observation,
            'authorization': authorization})
        return self._terminal(action, 'SKIPPED', dispatched=False, approval_consumed=False,
            reason=reason, skip_observation=observation, authorization=authorization)

    def _refusal(self, action, stage, exc, authorization):
        if isinstance(exc, getattr(self.runtime, 'TargetSkip', ())):
            return self._skip(action, str(exc), exc.observation, authorization)
        return self._blocked(action, stage, exc)

    def grant(self, action, quote, replacement_uuid=None):
        argv = self._context(action)
        validate_replacement(action, replacement_uuid)
        if (not isinstance(quote, str) or len(quote.encode('utf-8')) > 1024 * 1024 or
                not hmac.compare_digest(hashlib.sha256(quote.encode('utf-8')).hexdigest(),
                                        self.policy['approval_sha256'])):
            raise GuardError('exact Allison approval quote digest mismatch')
        with self.store.lock(create=True):
            self._unused(action)
            if self.store.exists(self.store.note_name(action)):
                raise GuardError('note already exists; replacement is prohibited')
            outcomes = self._outcomes(action)
            authorization = {'approval_quote': quote,
                             'approval_sha256': self.policy['approval_sha256'],
                             'argv_sha256': digest(argv)}
            try:
                self.runtime.precheck(action, replacement_uuid=replacement_uuid,
                                      outcomes=outcomes, proof=True)
                identity = self.runtime.identity(action)
            except Exception as exc:
                return self._refusal(action, 'grant precheck', exc, authorization)
            now = self._now()
            note = {'schema': 1, 'note_id': secrets.token_hex(32), 'single_use': True,
                    'task_id': self.policy['task_id'], 'action': action,
                    'policy_sha256': self.policy_digest, 'argv_sha256': digest(argv),
                    'identity': identity, 'identity_sha256': digest(identity),
                    'approval_quote': quote, 'approval_sha256': self.policy['approval_sha256'],
                    'created_epoch': now, 'expires_epoch': now + TTL_SECONDS,
                    'ttl_seconds': TTL_SECONDS, 'replacement_uuid': replacement_uuid}
            self.store.append_audit('GRANT', {'action': action, 'note': note, 'note_sha256': digest(note)})
            self.store.create(self.store.note_name(action), note)
            return {'status': 'GRANTED', 'action': action, 'note': note}

    def _validate_note(self, action, argv, note):
        required = {'schema', 'note_id', 'single_use', 'task_id', 'action', 'policy_sha256',
                    'argv_sha256', 'identity', 'identity_sha256', 'approval_quote', 'approval_sha256',
                    'created_epoch', 'expires_epoch', 'ttl_seconds', 'replacement_uuid'}
        if not isinstance(note, dict) or set(note) != required:
            raise GuardError('invalid operation-note schema')
        expected = {'schema': 1, 'single_use': True, 'task_id': self.policy['task_id'],
                    'action': action, 'policy_sha256': self.policy_digest,
                    'argv_sha256': digest(argv), 'ttl_seconds': TTL_SECONDS,
                    'approval_sha256': self.policy['approval_sha256']}
        if any(note[k] != v or type(note[k]) is not type(v) for k, v in expected.items()):
            raise GuardError('operation-note binding mismatch')
        if (not re.fullmatch(r'[a-f0-9]{64}', str(note['note_id'])) or
                digest(note['identity']) != note['identity_sha256'] or
                not isinstance(note['approval_quote'], str) or
                hashlib.sha256(note['approval_quote'].encode('utf-8')).hexdigest() != note['approval_sha256']):
            raise GuardError('note identity or approval integrity failure')
        validate_replacement(action, note['replacement_uuid'])
        self._expiry(note)
        if not any(r['event'] == 'GRANT' and r['payload'].get('note_sha256') == digest(note)
                   and r['payload'].get('action') == action for r in self.store.audit_records()):
            raise GuardError('note lacks exact durable grant audit')

    def _expiry(self, note):
        created, expires = note['created_epoch'], note['expires_epoch']
        if any(isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t)
               for t in (created, expires)):
            raise GuardError('invalid note timestamp')
        now = self._now()
        if expires - created != TTL_SECONDS or now < created or now >= expires:
            raise GuardError('note expired, from the future, or invalid lifetime')

    def _terminal(self, action, status, **fields):
        finished = self._now()
        outcome = {'schema': 1, 'status': status, 'action': action,
                   'task_id': self.policy['task_id'], 'policy_sha256': self.policy_digest,
                   'recorded_epoch': finished, 'finished_epoch': finished, **fields}
        self.store.create(self.store.outcome_name(action), outcome)
        self.store.append_audit('TERMINAL', {'action': action, 'status': status,
                                           'outcome_sha256': digest(outcome)})
        return outcome

    def execute(self, action):
        argv = self._context(action)
        with self.store.lock(create=False):
            self._unused(action)
            note = self.store.read(self.store.note_name(action))
            self._validate_note(action, argv, note)
            outcomes = self._outcomes(action)
            replacement = note['replacement_uuid']
            try:
                prior = self.runtime.precheck(action, replacement_uuid=replacement,
                                              outcomes=outcomes, proof=True)
                identity = self.runtime.identity(action)
            except Exception as exc:
                return self._refusal(action, 'execution precheck', exc,
                                     {'note_sha256': digest(note), 'note': note})
            if identity != note['identity']:
                return self._skip(action, 'fresh identity differs from approval binding',
                                  self.runtime.target_observation(action),
                                  {'note_sha256': digest(note), 'note': note})
            self._expiry(note)
            self.store.append_audit('PREPARED', {'action': action, 'note': note,
                                               'argv': argv, 'preconditions': prior})
            # This exclusively created tombstone is NEVER removed, even on crash.
            claim = {'schema': 1, 'status': 'CLAIMED', 'action': action,
                     'task_id': self.policy['task_id'], 'policy_sha256': self.policy_digest,
                     'note_sha256': digest(note), 'claimed_epoch': self._now()}
            self.store.create(self.store.claim_name(action), claim)
            self.store.append_audit('CLAIMED', claim)
            try:
                dispatch_state = self.runtime.dispatch_check(action, prior,
                    replacement_uuid=replacement, outcomes=outcomes)
                self.runtime.context_check()
                self._expiry(note)
                if self.runtime.identity(action) != note['identity']:
                    raise GuardError('target identity changed at dispatch boundary')
                self.store.append_audit('DISPATCHING', {'action': action, 'argv': argv,
                    'note_sha256': digest(note), 'dispatch_state': dispatch_state})
            except Exception as exc:
                return self._terminal(action, 'FAILED', dispatched=False, approval_consumed=False,
                                      claim_irreversible=True, reason=str(exc))
            try:
                child = self.runtime.dispatch(action, argv)
            except BaseException as exc:
                return self._terminal(action, 'AMBIGUOUS', dispatched=True, approval_consumed=True,
                                      claim_irreversible=True, reason=str(exc))
            try:
                after = self.runtime.postcheck(action, prior,
                    replacement_uuid=replacement, outcomes=outcomes)
                verified = (isinstance(child, dict) and type(child.get('returncode')) is int and
                            child['returncode'] == 0 and isinstance(after, dict) and
                            after.get('verified') is True)
                return self._terminal(action, 'VERIFIED' if verified else 'FAILED',
                    dispatched=True, approval_consumed=True, claim_irreversible=True,
                    child=child, preconditions=prior, postconditions=after,
                    note_sha256=digest(note))
            except Exception as exc:
                # If terminal persistence itself failed, a claim still blocks replay.
                if self.store.exists(self.store.outcome_name(action)):
                    raise GuardError('terminal record/audit could not be completed') from exc
                return self._terminal(action, 'FAILED', dispatched=True, approval_consumed=True,
                    claim_irreversible=True, child=child, reason=str(exc), note_sha256=digest(note))


def trusted_read(path):
    """Load only fixed installed code/config, without symlinks or writable peers."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise GuardError('untrusted installed path')
    for parent in reversed(path.parents):
        s = parent.lstat()
        if (not stat.S_ISDIR(s.st_mode) or s.st_uid not in (0, os.getuid()) or
                stat.S_IMODE(s.st_mode) & 0o022):
            raise GuardError('untrusted installed parent')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        s = os.fstat(fd)
        if (not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or s.st_nlink != 1 or
                stat.S_IMODE(s.st_mode) & 0o022 or s.st_size > MAX_RECORD_BYTES):
            raise GuardError('untrusted installed file')
        with os.fdopen(fd, 'rb', closefd=False) as f:
            return f.read(MAX_RECORD_BYTES + 1)
    finally:
        os.close(fd)


def public_result(result):
    """Project private receipts onto a fixed, non-sensitive CLI schema.

    Approval text, notes, identities, reasons, digests and child output remain
    only in the private transaction records. Never serialize the receipt itself.
    """
    if type(result) is not dict:
        raise GuardError('invalid public result')
    statuses = {value: value for value in (
        'PREVIEW', 'GRANTED', 'VERIFIED', 'SKIPPED', 'FAILED', 'AMBIGUOUS')}
    actions = {'npx:' + key: 'npx:' + key for key in ALLOWED_KEYS}
    actions['snapshot:131322'] = 'snapshot:131322'
    status, action = result.get('status'), result.get('action')
    if (type(status) is not str or status not in statuses or
            type(action) is not str or action not in actions):
        raise GuardError('invalid public status or action')
    # Emit values from the finite tables, not arbitrary caller-provided strings.
    public = {'status': statuses[status], 'action': actions[action]}
    for field in ('dispatched', 'approval_consumed', 'claim_irreversible',
                  'consumes_note', 'binding_required'):
        if field in result:
            if type(result[field]) is not bool:
                raise GuardError('invalid public status flag')
            public[field] = True if result[field] else False
    if 'child' in result:
        child = result['child']
        if type(child) is not dict:
            raise GuardError('invalid public child status')
        if 'returncode' in child:
            code = child['returncode']
            if type(code) is not int or not -255 <= code <= 255:
                raise GuardError('invalid public vendor return code')
            public['vendor_returncode'] = code
    return public


def emit_public_result(result):
    public = public_result(result)
    print(json.dumps(public, sort_keys=True, allow_nan=False))
    return 0 if public['status'] in ('PREVIEW', 'GRANTED', 'VERIFIED', 'SKIPPED') else 2


def emit_blocked():
    # Exception messages can include private filesystem or vendor data.
    print('{"code": "M4_GUARD_BLOCKED", "status": "BLOCKED"}', file=sys.stderr)
    return 2


def main(args=None):
    args = list(sys.argv[1:] if args is None else args)
    try:
        if Path(__file__) != EXECUTOR_PATH or not sys.flags.isolated:
            raise GuardError('production entry requires fixed installed path and isolated Python')
        if not args or args[0] not in ('execute', 'preview', 'grant'):
            raise GuardError('unknown private mode')
        mode = args[0]
        if len(args) not in ((2, 3) if mode == 'grant' else (2,)):
            raise GuardError('invalid argument count')
        action = validate_action(args[1])
        if len(args) == 3 and action != 'snapshot:131322':
            raise GuardError('replacement UUID is only valid for snapshot grant')
        raw = trusted_read(POLICY_PATH)
        if hashlib.sha256(raw).hexdigest() != POLICY_SHA256:
            raise GuardError('reviewed policy digest mismatch')
        policy = strict_json(raw)
        runtime_source = trusted_read(RUNTIME_PATH)
        if (not isinstance(policy, dict) or
                not re.fullmatch(r'[a-f0-9]{64}', str(policy.get('runtime_sha256'))) or
                not hmac.compare_digest(hashlib.sha256(runtime_source).hexdigest(),
                                        policy['runtime_sha256'])):
            raise GuardError('reviewed runtime source digest mismatch')
        spec = importlib.util.spec_from_file_location('m4_batch2_runtime', RUNTIME_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        # Execute the exact bytes read with no-follow checks, not a second path read.
        exec(compile(runtime_source, str(RUNTIME_PATH), 'exec'), module.__dict__)
        runtime = module.Runtime(policy)
        executor = Executor(policy, runtime, SecureStore(STATE_DIR), POLICY_SHA256)
        if mode == 'preview':
            result = executor.preview(action)
        elif mode == 'grant':
            quote = sys.stdin.read(1024 * 1024 + 1)
            result = executor.grant(action, quote, args[2] if len(args) == 3 else None)
        else:
            result = executor.execute(action)
        return emit_public_result(result)
    except Exception:
        return emit_blocked()


if __name__ == '__main__':
    raise SystemExit(main())
