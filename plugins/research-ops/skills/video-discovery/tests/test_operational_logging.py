import ast
import builtins
import io
import json
import shutil
import socket
import sys
from pathlib import Path

import pytest
import requests

import operational_logging as oplog
from operational_logging import (EVENTS, MAX_COUNT, MAX_DURATION_MS, SCHEMA, OperationalLogError,
                                 OperationalRun, build_event, emit, format_event, new_run_id)

RUN = '0123456789abcdef0123456789abcdef'
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'

# Synthetic sensitive fixtures. Token-like values are assembled at runtime so the
# repository secret scanner never sees a contiguous credential pattern.
SENSITIVE = {
    'email': 'jane.doe.synthetic@example.com',
    'phone': '+1 555 010 0199',
    'token': 'ghp' + '_' + 'Zx9' * 12,
    'bearer': 'Bearer ' + 'eyJ' + 'hbGciOi' + 'Q' * 24,
    'private_url': 'http://192.168.10.20/private/course/lesson-3?student=42',
    'path': '/home/jane/clients/acme-course/transcript.txt',
    'transcript': 'Welcome back to module three of the paid course, today we cover pricing.',
    'exception': 'Traceback: ConnectionError for https://intranet.example/secret?key=abc',
}


def fixed_clock(*values):
    it = iter(values)
    return lambda: next(it)


def lines(text):
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# 1. Deterministic schema and bounded values.

def test_deterministic_compact_sorted_json():
    line = format_event('discovery_finished', RUN, outcome='success', duration_ms=1500,
                        requests=12, candidates=3, stopped_domains=1)
    assert line == ('{"candidates":3,"duration_ms":1500,"event":"discovery_finished","outcome":"success",'
                    '"requests":12,"run_id":"' + RUN + '","schema":"' + SCHEMA + '","stopped_domains":1}')
    assert line == format_event('discovery_finished', RUN, stopped_domains=1, candidates=3,
                                duration_ms=1500, requests=12, outcome='success')


def test_started_event_has_only_envelope():
    assert build_event('probe_started', RUN) == {'schema': SCHEMA, 'event': 'probe_started', 'run_id': RUN}


def test_event_enum_is_fixed():
    assert set(EVENTS) == {'discovery_started', 'discovery_finished', 'probe_started', 'probe_finished'}
    with pytest.raises(OperationalLogError):
        build_event('discovery_progress', RUN)


def test_counts_and_duration_are_clamped_to_bounds():
    record = build_event('probe_finished', RUN, outcome='failure', duration_ms=10**15,
                         records_checked=10**12, samples_decoded=0)
    assert record['duration_ms'] == MAX_DURATION_MS
    assert record['records_checked'] == MAX_COUNT
    assert record['samples_decoded'] == 0


@pytest.mark.parametrize('value', [-1, 1.5, '3', True, None, [1], {'n': 1}])
def test_non_integer_or_negative_counts_rejected(value):
    with pytest.raises(OperationalLogError):
        build_event('discovery_finished', RUN, outcome='success', duration_ms=1, candidates=value)


@pytest.mark.parametrize('outcome', ['ok', 'SUCCESS', 1, None, ''])
def test_outcome_enum(outcome):
    with pytest.raises(OperationalLogError):
        build_event('discovery_finished', RUN, outcome=outcome, duration_ms=1)


def test_finished_requires_outcome_and_duration():
    with pytest.raises(OperationalLogError):
        build_event('discovery_finished', RUN, candidates=1)


def test_counts_belong_to_their_event():
    with pytest.raises(OperationalLogError):
        build_event('probe_finished', RUN, outcome='success', duration_ms=1, candidates=1)
    with pytest.raises(OperationalLogError):
        build_event('discovery_started', RUN, candidates=1)


@pytest.mark.parametrize('run_id', ['', 'abc', RUN.upper(), RUN + '0', 'g' * 32, 123, None])
def test_run_id_must_be_opaque_hex(run_id):
    with pytest.raises(OperationalLogError):
        build_event('discovery_started', run_id)


def test_generated_run_ids_are_opaque_and_unique():
    ids = {new_run_id() for _ in range(50)}
    assert len(ids) == 50 and all(oplog.RUN_ID.fullmatch(i) for i in ids)


# 2. Sensitive fixtures and unexpected keys are rejected and never echoed.

def attempts(value):
    yield lambda: build_event(value, RUN)
    yield lambda: build_event('discovery_started', value)
    yield lambda: build_event('discovery_finished', RUN, outcome=value, duration_ms=1)
    yield lambda: build_event('discovery_finished', RUN, outcome='success', duration_ms=value)
    yield lambda: build_event('discovery_finished', RUN, outcome='success', duration_ms=1, candidates=value)
    yield lambda: build_event('discovery_finished', RUN, outcome='success', duration_ms=1, detail=value)
    yield lambda: build_event('discovery_finished', RUN, outcome='success', duration_ms=1, url=value)
    yield lambda: build_event('discovery_finished', RUN, outcome='success', duration_ms=1, **{value: 1})
    yield lambda: emit('discovery_finished', RUN, outcome='success', duration_ms=1, message=value)


@pytest.mark.parametrize('name', sorted(SENSITIVE))
def test_sensitive_values_rejected_and_not_echoed(name, capsys):
    value = SENSITIVE[name]
    for attempt in attempts(value):
        with pytest.raises(OperationalLogError) as caught:
            attempt()
        assert value not in str(caught.value) and value not in repr(caught.value)
        assert caught.value.args and all(value not in str(a) for a in caught.value.args)
    out, err = capsys.readouterr()
    assert out == '' and err == ''


@pytest.mark.parametrize('key', ['title', 'url', 'path', 'prompt', 'text', 'body', 'exception', 'email', 'user', 'token'])
def test_unexpected_keys_rejected_by_default(key):
    with pytest.raises(OperationalLogError):
        build_event('discovery_finished', RUN, outcome='success', duration_ms=1, **{key: 0})


@pytest.mark.parametrize('name', sorted(SENSITIVE))
def test_run_omits_exception_text_and_bad_fields(name, capsys):
    value = SENSITIVE[name]
    with pytest.raises(RuntimeError):
        with OperationalRun('discovery', run_id=RUN, clock=fixed_clock(10.0, 10.25)) as op:
            op.record(candidates=2, note=value)
            raise RuntimeError(value)
    out, err = capsys.readouterr()
    assert out == ''
    assert value not in err
    assert lines(err) == [
        {'schema': SCHEMA, 'event': 'discovery_started', 'run_id': RUN},
        {'schema': SCHEMA, 'event': 'discovery_finished', 'run_id': RUN, 'outcome': 'failure', 'duration_ms': 250},
    ]


def test_run_success_and_exit_codes():
    stream = io.StringIO()
    with OperationalRun('probe', stream=stream, run_id=RUN, clock=fixed_clock(1.0, 3.0)) as op:
        op.record(records_checked=4, samples_decoded=1)
    assert lines(stream.getvalue())[-1] == {'schema': SCHEMA, 'event': 'probe_finished', 'run_id': RUN,
                                            'outcome': 'success', 'duration_ms': 2000,
                                            'records_checked': 4, 'samples_decoded': 1}
    for code, outcome in ((None, 'success'), (0, 'success'), (2, 'failure'), (SENSITIVE['path'], 'failure')):
        stream = io.StringIO()
        with pytest.raises(SystemExit):
            with OperationalRun('probe', stream=stream, run_id=RUN, clock=fixed_clock(0.0, 0.0)):
                raise SystemExit(code)
        assert lines(stream.getvalue())[-1]['outcome'] == outcome
        assert SENSITIVE['path'] not in stream.getvalue()


def test_run_rejects_unknown_kind():
    with pytest.raises(OperationalLogError):
        OperationalRun('upload')


def test_broken_stream_does_not_change_behavior():
    class Broken:
        def write(self, _):
            raise OSError('closed')
        def flush(self):
            pass
    with OperationalRun('probe', stream=Broken()):
        result = 'unchanged'
    assert result == 'unchanged'


# 3. No network, provider write, file read or content-bearing output.

def test_logger_imports_only_local_stdlib():
    tree = ast.parse((SCRIPTS / 'operational_logging.py').read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split('.')[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or '').split('.')[0])
    assert imported == {'json', 're', 'secrets', 'sys', 'time'}


@pytest.fixture
def no_io(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('forbidden I/O')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    monkeypatch.setattr(requests.Session, 'request', forbidden)
    monkeypatch.setattr(builtins, 'open', forbidden)
    for name in ('open', 'read_text', 'read_bytes', 'write_text', 'write_bytes'):
        monkeypatch.setattr(Path, name, forbidden)


def test_logger_performs_no_network_or_file_io(no_io, capsys):
    emit('discovery_started', RUN)
    with OperationalRun('discovery', run_id=RUN) as op:
        op.record(candidates=1, requests=2, stopped_domains=0)
    out, err = capsys.readouterr()
    assert out == '' and len(lines(err)) == 3


def discovery_args(tmp_path):
    return ['video_discovery.py', '--creator', 'Example Creator', '--youtube', 'https://youtube.com/@example',
            '--vimeo', 'https://vimeo.com/example/videos', '--website', 'example.com', '--output', str(tmp_path / 'out')]


def test_discovery_main_emits_only_operational_metadata(tmp_path, monkeypatch, capsys):
    import video_discovery

    class FakeInvestigation:
        def __init__(self, args):
            self.catalog = type('C', (), {'records': {('youtube', 'AbCdEf123_-'): object()}})()
            self.http = type('H', (), {'counts': {'example.com': 5, 'youtube.com': 2}, 'stopped': {'youtube.com': SENSITIVE['private_url']}})()
        def run(self):
            print('Crawl ok: https://example.com/', flush=True)

    monkeypatch.setattr(video_discovery, 'Investigation', FakeInvestigation)
    monkeypatch.setattr(sys, 'argv', discovery_args(tmp_path))
    video_discovery.main()
    out, err = capsys.readouterr()
    assert out == 'Crawl ok: https://example.com/\n'
    events = lines(err)
    assert [e['event'] for e in events] == ['discovery_started', 'discovery_finished']
    finished = events[-1]
    assert finished['outcome'] == 'success' and finished['candidates'] == 1
    assert finished['requests'] == 7 and finished['stopped_domains'] == 1
    assert set(finished) == {'schema', 'event', 'run_id', 'outcome', 'duration_ms', 'candidates', 'requests', 'stopped_domains'}
    assert 'example' not in err and str(tmp_path) not in err


def test_discovery_main_failure_keeps_exception_and_hides_text(tmp_path, monkeypatch, capsys):
    import video_discovery

    class Failing:
        def __init__(self, args):
            self.catalog = type('C', (), {'records': {}})()
            self.http = type('H', (), {'counts': {}, 'stopped': {}})()
        def run(self):
            raise RuntimeError(SENSITIVE['exception'])

    monkeypatch.setattr(video_discovery, 'Investigation', Failing)
    monkeypatch.setattr(sys, 'argv', discovery_args(tmp_path))
    with pytest.raises(RuntimeError, match='Traceback'):
        video_discovery.main()
    out, err = capsys.readouterr()
    assert out == '' and SENSITIVE['exception'] not in err
    assert lines(err)[-1]['outcome'] == 'failure'


def test_discovery_main_existing_output_still_refused(tmp_path, monkeypatch, capsys):
    import video_discovery
    (tmp_path / 'out').mkdir()
    (tmp_path / 'out' / 'catalog.json').write_text('{}')
    monkeypatch.setattr(sys, 'argv', discovery_args(tmp_path))
    with pytest.raises(SystemExit) as caught:
        video_discovery.main()
    assert caught.value.code == 'Use a fresh output directory to preserve prior evidence'
    out, err = capsys.readouterr()
    assert out == '' and str(tmp_path) not in err
    assert [e['outcome'] for e in lines(err) if 'outcome' in e] == ['failure']


def make_catalog(tmp_path, monkeypatch):
    import video_discovery
    monkeypatch.setattr(video_discovery, 'now', lambda: '2026-01-01T00:00:00+00:00')
    args = video_discovery.parser().parse_args(discovery_args(tmp_path)[1:])
    args.output = str(tmp_path / 'out')
    inv = video_discovery.Investigation(args)
    inv.catalog.add(video_discovery.Reference('youtube', 'AbCdEf123_-', 'https://www.youtube.com/watch?v=AbCdEf123_-'),
                    'https://example.com/', 'website_source')
    inv.export()
    return tmp_path / 'out'


def run_probe(out, monkeypatch, capsys, stub_logging):
    import probe_media
    if stub_logging:
        class Silent:
            def __init__(self, kind):
                pass
            def __enter__(self):
                return type('O', (), {'record': lambda self, **kw: None})()
            def __exit__(self, *exc):
                return False
        monkeypatch.setattr(probe_media, 'OperationalRun', Silent)
    else:
        monkeypatch.setattr(probe_media, 'OperationalRun', OperationalRun)
    def forbidden(*args, **kwargs):
        raise AssertionError('network attempted')
    monkeypatch.setattr(requests.Session, 'request', forbidden)
    monkeypatch.setattr(requests.Session, 'get', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    monkeypatch.setattr(sys, 'argv', ['probe_media.py', str(out)])
    capsys.readouterr()
    probe_media.main()
    result = capsys.readouterr()
    return result.out, result.err, (out / 'catalog.json').read_text()


def test_probe_behavior_unchanged_and_offline(tmp_path, monkeypatch, capsys):
    out = make_catalog(tmp_path, monkeypatch)
    (out / 'requests.jsonl').unlink(missing_ok=True)
    baseline_dir = tmp_path / 'baseline'
    shutil.copytree(out, baseline_dir)
    base_out, base_err, base_catalog = run_probe(baseline_dir, monkeypatch, capsys, stub_logging=True)
    new_out, new_err, new_catalog = run_probe(out, monkeypatch, capsys, stub_logging=False)
    assert new_out == base_out and base_err == ''
    assert json.loads(new_catalog)['records'] == json.loads(base_catalog)['records']
    assert json.loads(new_catalog)['notes'] == json.loads(base_catalog)['notes']
    events = lines(new_err)
    assert [e['event'] for e in events] == ['probe_started', 'probe_finished']
    assert events[-1]['outcome'] == 'success'
    assert events[-1]['records_checked'] == 0 and events[-1]['samples_decoded'] == 0
    assert 'AbCdEf123_-' not in new_err and 'example' not in new_err and str(tmp_path) not in new_err

def test_probe_counts_sampled_records(tmp_path, monkeypatch, capsys):
    import probe_media
    import video_discovery
    out = make_catalog(tmp_path, monkeypatch)
    data = json.loads((out / 'catalog.json').read_text())
    url = 'https://cdn.example.com/private-lesson.mp4'
    record = video_discovery.Record('direct', 'd' * 20, url)
    record.checks.append(dict(method='media_head', result='media_endpoint_accessible', headers={'content-length': '10000000'}))
    data['records'].append(video_discovery.asdict(record))
    (out / 'catalog.json').write_text(json.dumps(data))
    monkeypatch.setattr(probe_media, 'sample', lambda http, u, size: (b'\0' * size, 'partial_media_sample'))
    monkeypatch.setattr(probe_media, 'decode_frame', lambda body: (True, SENSITIVE['exception']))
    new_out, new_err, _ = run_probe(out, monkeypatch, capsys, stub_logging=False)
    assert new_out.startswith('d' * 20 + ' sample_frame_decoded ')
    finished = lines(new_err)[-1]
    assert finished['records_checked'] == 1 and finished['samples_decoded'] == 1
    assert url not in new_err and 'd' * 20 not in new_err and SENSITIVE['exception'] not in new_err
