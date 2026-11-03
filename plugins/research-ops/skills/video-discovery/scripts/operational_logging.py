"""Privacy-safe operational status events for the video-discovery scripts.

Each event is one JSON line on stderr. Only a fixed allowlist of non-content
fields is accepted: the event name, an opaque random run identifier, a
success/failure outcome, a duration and bounded counts. Anything else is
rejected, and rejection errors never repeat the offending key or value, so no
URL, path, title, transcript, exception text or credential can reach the log.
Nothing is written to files and nothing is sent over the network.
"""
import json
import re
import secrets
import sys
import time

SCHEMA = 'video-discovery.operational.v1'
OUTCOMES = frozenset({'success', 'failure'})
MAX_COUNT = 1_000_000
MAX_DURATION_MS = 7 * 24 * 60 * 60 * 1000
RUN_ID = re.compile(r'[0-9a-f]{32}')

_FINISHED = frozenset({'outcome', 'duration_ms'})
COUNT_FIELDS = {
    'discovery': frozenset({'candidates', 'requests', 'stopped_domains'}),
    'probe': frozenset({'records_checked', 'samples_decoded'}),
}
EVENTS = {
    **{kind + '_started': frozenset() for kind in COUNT_FIELDS},
    **{kind + '_finished': _FINISHED | counts for kind, counts in COUNT_FIELDS.items()},
}
REQUIRED = {name: (_FINISHED if name.endswith('_finished') else frozenset()) for name in EVENTS}


class OperationalLogError(ValueError):
    """Raised with a fixed message only; never carries the rejected input."""


def new_run_id():
    return secrets.token_hex(16)


def _bounded_int(value, maximum):
    # bool is an int subclass; True must not pass as a count.
    if type(value) is not int or value < 0:
        raise OperationalLogError('operational field value rejected')
    return min(value, maximum)


def build_event(event, run_id, **fields):
    """Return the validated event as a dict, or raise OperationalLogError."""
    if not isinstance(event, str) or event not in EVENTS:
        raise OperationalLogError('operational event rejected')
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise OperationalLogError('operational run identifier rejected')
    allowed = EVENTS[event]
    if any(not isinstance(key, str) or key not in allowed for key in fields):
        raise OperationalLogError('operational field rejected')
    if not REQUIRED[event] <= fields.keys():
        raise OperationalLogError('operational field missing')
    record = {'schema': SCHEMA, 'event': event, 'run_id': run_id}
    for key, value in fields.items():
        if key == 'outcome':
            if not isinstance(value, str) or value not in OUTCOMES:
                raise OperationalLogError('operational field value rejected')
            record[key] = value
        elif key == 'duration_ms':
            record[key] = _bounded_int(value, MAX_DURATION_MS)
        else:
            record[key] = _bounded_int(value, MAX_COUNT)
    return record


def format_event(event, run_id, **fields):
    return json.dumps(build_event(event, run_id, **fields), sort_keys=True, separators=(',', ':'))


def emit(event, run_id, stream=None, **fields):
    """Validate, then write one line. Raises OperationalLogError before writing anything."""
    line = format_event(event, run_id, **fields)
    stream = sys.stderr if stream is None else stream
    try:
        stream.write(line + '\n')
        stream.flush()
    except (OSError, ValueError):
        pass
    return line


class OperationalRun:
    """Context manager emitting <kind>_started and <kind>_finished.

    The outcome depends only on whether the block raised; the exception itself
    is never inspected beyond SystemExit's exit code and always propagates.
    Logging problems never change the script: an invalid event is omitted.
    """

    def __init__(self, kind, stream=None, clock=time.monotonic, run_id=None):
        if kind not in COUNT_FIELDS:
            raise OperationalLogError('operational run kind rejected')
        self.kind = kind
        self.stream = stream
        self.clock = clock
        self.run_id = run_id or new_run_id()
        self.counts = {}
        self.started = None

    def record(self, **counts):
        self.counts.update(counts)

    def _emit(self, event, **fields):
        try:
            return emit(event, self.run_id, stream=self.stream, **fields)
        except OperationalLogError:
            return None

    def __enter__(self):
        self.started = self.clock()
        self._emit(self.kind + '_started')
        return self

    def __exit__(self, exc_type, exc, tb):
        success = exc_type is None or (issubclass(exc_type, SystemExit) and exc.code in (None, 0))
        elapsed = max(0, int(round((self.clock() - self.started) * 1000)))
        fields = dict(outcome='success' if success else 'failure', duration_ms=elapsed)
        if self._emit(self.kind + '_finished', **fields, **self.counts) is None and self.counts:
            self._emit(self.kind + '_finished', **fields)
        return False
