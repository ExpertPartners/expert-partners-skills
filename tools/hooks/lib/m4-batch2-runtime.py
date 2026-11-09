"""Fixed M4 Batch 2 runtime predicates and vendor adapter. No CLI or test switch."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import subprocess
import time

HOME = '/Users/allisongaddy'
DATA = '/System/Volumes/Data'
NODE = '/opt/homebrew/Cellar/node/25.9.0_2/bin/node'
NPM = '/opt/homebrew/lib/node_modules/npm/bin/npm-cli.js'
NPX = HOME + '/.npm/_npx'
KEYS = tuple('3fac9f70aa5c9ccf 03676be6c5876144 67eb4586ca667318 705bc6b22212b352 9eac9498388ae25e 96a8727b140d6939 bce731a0395adf49 cc2145a2fe1558fa 7f312557c12f11a3 3f410cde517faec3 a3586cc356aa4ace 1ce9283feb7d83f2 8003d8991b0d346b 33664ddc0e10cefa dcf0514efa8ecddd 1bf7c3c15bf47d04 bd03aaf280724e38 f19f78a55038d137 69f9afb961c37556 705d23756ff7dacc ffe2131771d88588 1ddbeaccabfe00a4 32026684e21afda6 1a3c4333f3a90708 67a0730928194b24 e41f203b7505f1fb ac0ed6aa23b37c1e 9dc43daea2065b57'.split())
ACTIVE = ('6583fba12287d067', '9833c18b2d85bc59')
OLD_NAME = 'com.apple.TimeMachine.2026-09-23-131322.local'
OLD_UUID = 'FCA82852-B4F7-477B-B344-49DD9FB4660B'
CHILD_ENV = {'HOME': HOME, 'USER': 'allisongaddy', 'LOGNAME': 'allisongaddy',
             'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C', 'LC_ALL': 'C',
             'TMPDIR': '/private/tmp'}


class SafetyError(RuntimeError):
    pass


class TargetSkip(SafetyError):
    """An observed finite target is ineligible; never grants deletion authority."""
    def __init__(self, reason, observation):
        super().__init__(reason)
        self.observation = observation


def require(ok, reason):
    if not ok:
        raise SafetyError(reason)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def fixed_argv(policy, action):
    require(isinstance(action, str), 'action must be a string')
    require(policy['npx_keys'] == list(KEYS), 'registry allowlist mismatch')
    if action == 'snapshot:131322':
        return ['/usr/bin/tmutil', 'deletelocalsnapshots', '2026-09-23-131322']
    require(re.fullmatch(r'npx:[0-9a-f]{16}', action) is not None, 'invalid action grammar')
    key = action[4:]
    require(key in KEYS and key not in ACTIVE, 'unlisted or protected action')
    return [NODE, NPM, 'cache', 'npx', 'rm', key, '--cache', HOME + '/.npm']


class LocalFS:
    def exists(self, path):
        return os.path.lexists(path)

    def file_hash(self, path):
        with open(path, 'rb') as f:
            return hashlib.file_digest(f, 'sha256').hexdigest()

    def tree_hash(self, path):
        base = Path(path)
        require(base.is_dir() and not base.is_symlink(), 'invalid source tree')
        h = hashlib.sha256()
        for p in sorted(base.rglob('*')):
            rel = str(p.relative_to(base))
            if p.is_symlink():
                require(p.resolve().is_relative_to(base), 'external source symlink')
                item = ['link', rel, os.readlink(p)]
            elif p.is_file():
                item = ['file', rel, self.file_hash(p)]
            elif p.is_dir():
                item = ['directory', rel]
            else:
                raise SafetyError('special source file')
            h.update((json.dumps(item, separators=(',', ':')) + '\n').encode())
        return h.hexdigest()

    def _rows(self, root):
        root = Path(root)
        rows = []
        external = []
        errors = []
        for folder, dirs, files in os.walk(root, followlinks=False, onerror=lambda e: errors.append(str(e))):
            for name in sorted(dirs + files):
                p = Path(folder) / name
                s = p.lstat()
                row = [str(p.relative_to(root)), s.st_mode, s.st_ino, s.st_size, s.st_mtime_ns, s.st_blocks * 512]
                if stat.S_ISLNK(s.st_mode):
                    row.append(os.readlink(p))
                    if not p.resolve().is_relative_to(root):
                        external.append(str(p.relative_to(root)))
                elif not (stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode)):
                    external.append('special:' + str(p.relative_to(root)))
                rows.append(row)
        require(not errors, 'filesystem inventory incomplete')
        rows.sort()
        return hashlib.sha256(json.dumps(rows).encode()).hexdigest(), external

    def fingerprint(self, path):
        p = Path(path)
        if not p.exists() and not p.is_symlink():
            return {'exists': False, 'inode': None, 'metadata_sha256': None}
        require(not p.is_symlink(), 'protected path is a symlink')
        if p.is_dir():
            hashed, _ = self._rows(p)
        else:
            hashed = self.file_hash(p)
        return {'exists': True, 'inode': p.stat().st_ino, 'metadata_sha256': hashed}

    def identity(self, path):
        p = Path(path)
        require(str(p) == str(p.resolve()), 'target resolves through symlink')
        require(all(not x.is_symlink() for x in [p, *p.parents]), 'target ancestry symlink')
        require(p.is_dir(), 'target absent or not directory')
        hashed, external = self._rows(p)
        return {'path': str(p), 'exists': True, 'is_dir': True, 'no_symlinks': True,
                'inode': p.stat().st_ino, 'top_names': sorted(x.name for x in p.iterdir()),
                'metadata_sha256': hashed,
                'package_sha256': self.file_hash(p / 'package.json'),
                'lock_sha256': self.file_hash(p / 'package-lock.json'), 'external_links': external}

    def archives(self, root):
        p = Path(root)
        require(p.is_dir() and not p.is_symlink(), 'archive directory unavailable')
        result = []
        for f in sorted(p.glob('*.enc')):
            require(f.is_file() and not f.is_symlink(), 'archive identity ambiguous')
            s = f.stat()
            result.append({'name': f.name, 'bytes': s.st_size, 'mtime_ns': s.st_mtime_ns, 'inode': s.st_ino})
        return result

    def mkdir_mount(self, path):
        p = Path(path)
        require(str(p).startswith('/private/tmp/m4-batch2-restore-'), 'unexpected mount path')
        if not p.exists():
            p.mkdir(mode=0o700)
        s = p.lstat()
        require(stat.S_ISDIR(s.st_mode) and s.st_uid == os.getuid() and not (s.st_mode & 0o077), 'unsafe mount directory')
        require(not any(p.iterdir()), 'mount directory not empty')

    def snapshot_path_exists(self, mount, absolute_path):
        require(absolute_path.startswith(HOME + '/'), 'unexpected protected snapshot path')
        p = Path(mount) / absolute_path.lstrip('/')
        require(not p.is_symlink(), 'snapshot representative is a symlink')
        if p.is_file():
            with p.open('rb') as f:
                f.read(1)
        elif p.is_dir():
            next(p.iterdir(), None)
        return p.exists()

    def snapshot_identity(self, mount, absolute_path):
        require(absolute_path.startswith(NPX + '/'), 'unexpected snapshot target')
        observed = self.identity(str(Path(mount) / absolute_path.lstrip('/')))
        observed['path'] = absolute_path
        return observed


def real_runner(argv, *, timeout=60):
    result = subprocess.run(argv, shell=False, cwd=HOME, env=CHILD_ENV,
                            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    return {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}


class Runtime:
    TargetSkip = TargetSkip

    def __init__(self, policy, runner=None, fs=None, env=None):
        self.policy = policy
        self.runner = real_runner if runner is None else runner
        self.fs = LocalFS() if fs is None else fs
        self.env = os.environ if env is None else env

    def fixed_argv(self, action):
        return fixed_argv(self.policy, action)

    def context_check(self):
        require(self.env.get('CODEX_THREAD_ID') == self.policy['task_id'], 'wrong task')
        require(self.env.get('HOME') == HOME, 'wrong HOME')
        require(not self.fs.exists(HOME + '/.claude/pre-tool-use-enforcement-off'), 'guard disabled')
        forbidden = ('NODE_', 'NPM_CONFIG_', 'npm_config_', 'DYLD_', 'LD_', 'PYTHON',
                     'DELETION_APPROVAL_', 'M4_BATCH2_', 'BASH_FUNC_')
        names = {'BASH_ENV', 'ENV', 'PRE_TOOL_USE_OFF', 'NODE_PATH', 'NODE_OPTIONS', 'TZ'}
        require(not any(k in names or k.startswith(forbidden) for k in self.env), 'command-affecting environment override')
        require(self.policy['active_keys'] == list(ACTIVE), 'protected-key policy mismatch')

    def _run(self, argv, timeout=60):
        result = self.runner(argv, timeout=timeout)
        require(result['returncode'] == 0, 'read-only command failed: ' + argv[0] + ' ' + str(result['returncode']))
        return result

    def _plist(self, argv):
        return plistlib.loads(self._run(argv)['stdout'].encode())

    def _tools(self):
        seen = {}
        for path, expected in self.policy['tools'].items():
            actual = self.fs.file_hash(path)
            require(actual == expected, 'tool identity changed: ' + path)
            seen[path] = actual
        require(self.fs.tree_hash('/opt/homebrew/lib/node_modules/npm') == self.policy['npm_tree_sha256'], 'npm dependency/source tree changed')
        return seen

    def _health(self):
        a = self._run(['/usr/local/bin/docker', 'inspect', '--format', '{{.State.Status}} {{.State.Health.Status}}', 'supabase_db_FounderCommandCenter'])
        b = self._run(['/usr/local/bin/docker', 'exec', 'supabase_db_FounderCommandCenter', 'pg_isready', '-U', 'postgres', '-d', 'postgres'])
        require(a['stdout'].strip() == 'running healthy' and 'accepting connections' in b['stdout'], 'database health regression')
        return {'container': a['stdout'].strip(), 'postgres': b['stdout'].strip()}

    def _inventory(self):
        containers = self._plist(['/usr/sbin/diskutil', 'apfs', 'list', '-plist'])['Containers']
        mounted = []
        for container in containers:
            for volume in container['Volumes']:
                info = self._plist(['/usr/sbin/diskutil', 'info', '-plist', volume['DeviceIdentifier']])
                point = info.get('MountPoint')
                if not point:
                    continue
                snap = self._plist(['/usr/sbin/diskutil', 'apfs', 'listSnapshots', point, '-plist'])
                require(isinstance(snap.get('Snapshots'), list), 'snapshot inventory incomplete')
                mounted.append({'volume_uuid': volume['APFSVolumeUUID'], 'device': volume['DeviceIdentifier'],
                                'mount': point, 'snapshots': [{'name': s['SnapshotName'], 'uuid': s['SnapshotUUID']} for s in snap['Snapshots']]})
        root = self._plist(['/usr/sbin/diskutil', 'info', '-plist', '/'])
        roots = self._plist(['/usr/sbin/diskutil', 'apfs', 'listSnapshots', '/', '-plist'])
        require(isinstance(roots.get('Snapshots'), list), 'boot inventory incomplete')
        systems = [v for c in containers for v in c['Volumes']
                   if v['APFSVolumeUUID'] == self.policy['boot_volume_uuid'] and 'System' in v.get('Roles', [])]
        require(len(systems) == 1, 'System volume identity ambiguous')
        system = systems[0]
        require(root['DeviceIdentifier'] == system['DeviceIdentifier'] or
                root['DeviceIdentifier'].startswith(system['DeviceIdentifier'] + 's'), 'boot volume mapping mismatch')
        if not any(v['mount'] == '/' for v in mounted):
            mounted.append({'volume_uuid': system['APFSVolumeUUID'], 'device': root['DeviceIdentifier'], 'mount': '/',
                            'snapshots': [{'name': s['SnapshotName'], 'uuid': s['SnapshotUUID']} for s in roots['Snapshots']]})
        data = self._plist(['/usr/sbin/diskutil', 'info', '-plist', DATA])
        require(data['VolumeUUID'] == self.policy['data_uuid'], 'Data volume mismatch')
        require(len([v for v in mounted if v['mount'] == DATA]) == 1, 'ambiguous Data mount')
        tm = self._run(['/usr/bin/tmutil', 'listlocalsnapshots', DATA])['stdout']
        data_snaps = next(v['snapshots'] for v in mounted if v['mount'] == DATA)
        for snap in data_snaps:
            if snap['name'].startswith('com.apple.TimeMachine.'):
                require(snap['name'] in tm.splitlines(), 'tmutil/diskutil disagreement')
        return {'volumes': sorted(mounted, key=lambda v: (v['mount'], v['volume_uuid'])),
                'mount_table': self._run(['/sbin/mount'])['stdout'], 'physical_free_bytes': data['APFSContainerFree']}

    def _snapset(self, inv):
        return {(v['volume_uuid'], s['name'], s['uuid']) for v in inv['volumes'] for s in v['snapshots']}

    def _snapshots_safe(self, inv, old_required=True):
        snaps = self._snapset(inv)
        for expected in self.policy['protected_snapshots']:
            require(tuple(expected) in snaps, 'protected snapshot changed: ' + expected[1])
        old = (self.policy['data_uuid'], OLD_NAME, OLD_UUID)
        require((old in snaps) == old_required, 'old snapshot presence/identity mismatch')
        matches = [x for x in snaps if x[1] == OLD_NAME]
        require(matches == [old] if old_required else not matches, 'target timestamp scope ambiguous')

    def target_observation(self, action):
        self.fixed_argv(action)
        require(action.startswith('npx:'), 'observation requires fixed npx target')
        key = action[4:]
        actual = self.fs.identity(NPX + '/' + key)
        require(actual['path'] == NPX + '/' + key and actual['exists'] and actual['is_dir'] and actual['no_symlinks'], 'target path invalid')
        require(actual['top_names'] == ['node_modules', 'package-lock.json', 'package.json'] and not actual['external_links'], 'unexpected non-package or external state')
        return actual

    def identity(self, action):
        self.fixed_argv(action)
        if action == 'snapshot:131322':
            return {'name': OLD_NAME, 'uuid': OLD_UUID, 'data_uuid': self.policy['data_uuid']}
        actual = self.target_observation(action)
        expected = self.policy['targets'][action[4:]]
        for field in ['inode', 'metadata_sha256', 'package_sha256', 'lock_sha256']:
            if actual[field] != expected[field]:
                raise TargetSkip('target changed: ' + field, actual)
        return {k: actual[k] for k in ['path', 'inode', 'metadata_sha256', 'package_sha256', 'lock_sha256']}

    def _consumers(self, action, observation):
        target = NPX + '/' + action[4:]
        ps = self._run(['/bin/ps', '-axo', 'pid=,ppid=,command='])
        require(bool(ps['stdout'].strip()) and not ps['stderr'].strip(), 'incomplete process inventory')
        active_process = False
        for line in ps['stdout'].splitlines():
            pieces = line.split(None, 2)
            require(len(pieces) == 3 and pieces[0].isdigit() and pieces[1].isdigit(), 'malformed process inventory')
            if target in pieces[2]:
                active_process = True
        handles = self._run(['/usr/sbin/lsof', '-nP', '-Fpcfnt'], timeout=90)
        require(bool(handles['stdout'].strip()) and handles['stdout'].endswith('\n')
                and not handles['stderr'].strip(), 'incomplete open-handle inventory')
        # -F frames each process with p/c and each file with f/t/n. Darwin's
        # audited non-path objects can have an empty n field; never infer that
        # an unnamed filesystem object is unrelated to the cleanup target.
        blank_name_types = {'NPOLICY', 'NEXUS', 'rte', 'PIPE'}
        filesystem_types = {'REG', 'DIR', 'LINK', 'FIFO', 'CHR', 'BLK'}
        process_seen = command_seen = file_seen = named_file = any_file = active_handle = False
        file_type = None
        for line in handles['stdout'].split('\n')[:-1]:
            require(bool(line) and not any(ord(c) < 32 or ord(c) == 127 for c in line),
                    'malformed open-handle inventory')
            tag, value = line[0], line[1:]
            if tag == 'p':
                if process_seen:
                    require(command_seen and file_seen and named_file, 'incomplete open-handle process group')
                require(re.fullmatch(r'[0-9]+', value) is not None, 'malformed open-handle PID')
                process_seen, command_seen, file_seen, named_file = True, False, False, False
                file_type = None
            elif tag == 'c':
                require(process_seen and not command_seen and not file_seen and bool(value.strip()),
                        'missing, duplicate or misplaced open-handle command')
                command_seen = True
            elif tag == 'f':
                require(process_seen and command_seen, 'open-handle descriptor without process/command')
                if file_seen:
                    require(named_file, 'unnamed open-handle descriptor')
                require(re.fullmatch(r'(?:[0-9]+[rwu]?|cwd|rtd|txt|mem|fp\.|twd)', value) is not None,
                        'malformed open-handle descriptor')
                file_seen = True
                named_file = False
                file_type = None
            elif tag == 't':
                require(process_seen and command_seen and file_seen and not named_file
                        and file_type is None, 'duplicate or misplaced open-handle type')
                require(re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*', value) is not None,
                        'missing or malformed open-handle type')
                file_type = value
            elif tag == 'n':
                require(process_seen and command_seen and file_seen and file_type is not None
                        and not named_file, 'duplicate or misplaced open-handle name')
                require(bool(value.strip()) or value == '' and file_type in blank_name_types,
                        'unnamed path-capable or unknown open-handle type')
                require(' -- ' not in value and not value.endswith('(?)'),
                        'ambiguous partial open-handle name')
                if file_type in filesystem_types:
                    require(value.startswith('/'), 'nonabsolute filesystem open-handle name')
                any_file = True
                named_file = True
                # A known or future type with a name still participates in
                # exact target matching; type never suppresses active evidence.
                if value == target or value.startswith(target + '/'):
                    active_handle = True
            else:
                raise SafetyError('unexpected open-handle field')
        require(process_seen and command_seen and file_seen and named_file and any_file,
                'open-handle inventory has an incomplete final process group')
        if active_process or active_handle:
            raise TargetSkip('active command consumer for target' if active_process else 'active open-handle consumer for target', observation)
        return {'process_inventory_complete': True, 'open_handle_inventory_complete': True,
                'process_inventory_sha256': hashlib.sha256(ps['stdout'].encode()).hexdigest(),
                'open_handle_inventory_sha256': hashlib.sha256(handles['stdout'].encode()).hexdigest()}

    def _protected(self, omit=None):
        result = {}
        for row in self.policy['protected_trees']:
            actual = self.fs.fingerprint(row['path'])
            require(actual == row['fingerprint'], 'protected tree changed: ' + row['path'])
            result[row['path']] = actual
        for path in [HOME + '/.npmrc', HOME + '/.npm/_cacache']:
            result[path] = self.fs.fingerprint(path)
        for key in KEYS:
            if key != omit:
                result[NPX + '/' + key] = self.fs.fingerprint(NPX + '/' + key)
        return result

    def _outcomes(self, outcomes):
        require(isinstance(outcomes, list) and len(outcomes) == len(KEYS), 'incomplete npx outcome receipts')
        by_key = {}
        for row in outcomes:
            action = row.get('action')
            require(isinstance(action, str) and action.startswith('npx:') and action[4:] in KEYS, 'unlisted npx receipt')
            key = action[4:]
            require(key not in by_key, 'duplicate npx receipt')
            require(row.get('task_id') == self.policy['task_id'] and row.get('status') in {'VERIFIED', 'SKIPPED'}, 'incomplete or failed npx receipt')
            require(isinstance(row.get('finished_epoch'), (int, float)) and row['finished_epoch'] > 0, 'receipt timestamp absent')
            if row['status'] == 'SKIPPED':
                require(bool(row.get('reason')), 'skip reason absent')
                require(isinstance(row.get('skip_observation'), dict), 'captured skip observation absent')
                require(self.target_observation(action) == row['skip_observation'], 'skipped target changed after receipt')
            else:
                require(not self.fs.exists(NPX + '/' + key), 'removed key present')
            by_key[key] = row
        require(set(by_key) == set(KEYS), 'missing npx receipt')
        return by_key

    def _replacement(self, inv, replacement_uuid, outcomes):
        require(isinstance(replacement_uuid, str) and re.fullmatch(r'[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}', replacement_uuid), 'invalid replacement UUID')
        require(replacement_uuid != OLD_UUID, 'replacement equals old snapshot')
        by_key = self._outcomes(outcomes)
        matches = [(v, s) for v in inv['volumes'] for s in v['snapshots'] if s['uuid'] == replacement_uuid]
        require(len(matches) == 1 and matches[0][0]['volume_uuid'] == self.policy['data_uuid'], 'replacement volume/UUID mismatch')
        volume, snapshot = matches[0]
        match = re.fullmatch(r'com\.apple\.TimeMachine\.(\d{4}-\d\d-\d\d-\d{6})\.local', snapshot['name'])
        require(match is not None, 'replacement name invalid')
        stamp = datetime.datetime.strptime(match[1], '%Y-%m-%d-%H%M%S').timestamp()
        require(stamp > max(r['finished_epoch'] for r in by_key.values()), 'replacement predates completed cleanup')
        return volume, snapshot, by_key

    def _mount_proof(self, volume, snap, by_key):
        mount = '/private/tmp/m4-batch2-restore-' + snap['uuid'].lower()
        self.fs.mkdir_mount(mount)
        before = self._run(['/sbin/mount'])['stdout']
        require((' on ' + mount + ' ') not in before, 'replacement mount already present')
        proof = {}
        try:
            self._run(['/sbin/mount_apfs', '-o', 'rdonly,nobrowse', '-s', snap['name'], '/dev/' + volume['device'], mount])
            rows = [x for x in self._run(['/sbin/mount'])['stdout'].splitlines() if (' on ' + mount + ' ') in x]
            require(len(rows) == 1 and ('read-only' in rows[0] or 'rdonly' in rows[0]), 'replacement not proven read-only')
            for path in self.policy['snapshot_representatives']:
                require(self.fs.snapshot_path_exists(mount, path), 'protected snapshot representative missing: ' + path)
            for key, row in by_key.items():
                exists = self.fs.snapshot_path_exists(mount, NPX + '/' + key)
                require(exists == (row['status'] == 'SKIPPED'), 'snapshot outcome mismatch: ' + key)
                if row['status'] == 'SKIPPED':
                    require(self.fs.snapshot_identity(mount, NPX + '/' + key) == row['skip_observation'], 'snapshot skipped target identity mismatch: ' + key)
            self._health()
            require(self.fs.archives(self.policy['archive_root']) == self.policy['archives'], 'archive drift during snapshot proof')
            proof = {'uuid': snap['uuid'], 'name': snap['name'], 'read_only': True, 'protected_accessible': True,
                     'all_npx_outcomes_match': True, 'mount_path': mount}
        finally:
            # A failed or timed-out mount command may already have attached.
            # Inspect the exact mount even when the command did not return success.
            attached = (' on ' + mount + ' ') in self._run(['/sbin/mount'])['stdout']
            if attached:
                self._run(['/sbin/umount', mount])
            require((' on ' + mount + ' ') not in self._run(['/sbin/mount'])['stdout'], 'replacement still mounted')
        proof['unmounted'] = True
        return proof

    def precheck(self, action, replacement_uuid=None, outcomes=None, proof=True):
        self.context_check()
        self.fixed_argv(action)
        tools = self._tools()
        health = self._health()
        archives = self.fs.archives(self.policy['archive_root'])
        require(archives == self.policy['archives'] and len(archives) == 18, 'recovery archive drift')
        inv = self._inventory()
        self._snapshots_safe(inv)
        protected = self._protected(action[4:] if action.startswith('npx:') else None)
        observation = consumers = None
        if action.startswith('npx:'):
            observation = self.target_observation(action)
            consumers = self._consumers(action, observation)
        identity = self.identity(action)
        result = {'identity': identity, 'tools': tools, 'health': health, 'archives': archives,
                  'inventory': inv, 'protected': protected, 'observed_epoch': time.time()}
        if action.startswith('npx:'):
            result['target_observation'] = observation
            result['consumers'] = consumers
        else:
            volume, snapshot, by_key = self._replacement(inv, replacement_uuid, outcomes)
            if proof:
                result['mount_proof'] = self._mount_proof(volume, snapshot, by_key)
        return result

    def dispatch_check(self, action, prior, replacement_uuid=None, outcomes=None):
        current = self.precheck(action, replacement_uuid, outcomes, proof=False)
        for key in ['identity', 'protected', 'archives', 'tools']:
            require(current[key] == prior[key], 'state changed at dispatch: ' + key)
        require(current['inventory']['volumes'] == prior['inventory']['volumes'], 'mounted volume/snapshot inventory changed at dispatch')
        require(current['inventory']['mount_table'] == prior['inventory']['mount_table'], 'mount inventory changed at dispatch')
        if action == 'snapshot:131322':
            require(prior.get('mount_proof', {}).get('uuid') == replacement_uuid and prior['mount_proof'].get('unmounted') is True, 'replacement verification not completed in invocation')
        return current

    def dispatch(self, action, argv):
        self.context_check()
        require(argv == self.fixed_argv(action), 'vendor argv mismatch')
        return self.runner(argv, timeout=180)

    def postcheck(self, action, prior, replacement_uuid=None, outcomes=None):
        health = self._health()
        archives = self.fs.archives(self.policy['archive_root'])
        require(archives == self.policy['archives'], 'archive drift after dispatch')
        inv = self._inventory()
        self._snapshots_safe(inv, old_required=action != 'snapshot:131322')
        expected_snaps = self._snapset(prior['inventory'])
        if action == 'snapshot:131322':
            expected_snaps.remove((self.policy['data_uuid'], OLD_NAME, OLD_UUID))
            require(any(x[2] == replacement_uuid for x in self._snapset(inv)), 'replacement lost')
        else:
            require(not self.fs.exists(NPX + '/' + action[4:]), 'target still exists after vendor operation')
        require(expected_snaps.issubset(self._snapset(inv)), 'unauthorized snapshot loss/change')
        protected = self._protected(action[4:] if action.startswith('npx:') else None)
        require(protected == prior['protected'], 'protected sibling/config/state changed')
        self._tools()
        return {'verified': True, 'health': health, 'archives': archives, 'inventory': inv,
                'protected': protected, 'finished_epoch': time.time(), 'retained_snapshot_yield_guarantee_bytes': 0}
