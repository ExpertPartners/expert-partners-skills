"""Bounded stdio MCP client. Owns only its unreaped subprocess group."""

import json
import os
import selectors
import signal
import subprocess
import time


class Refusal(Exception):
    """Static diagnostic code, never provider text or command arguments."""


class StdioClient:
    """One persistent launcher per instance. No token/env contents are returned or logged."""

    def __init__(self, command, env, timeout=20, cap=2097152, frame_cap=65536, script=None):
        script_read = script_write = None
        if script is not None:
            if type(script) is not bytes or not 0 < len(script) <= 65536:
                raise Refusal('script_cap')
            script_read, script_write = os.pipe()
            command = ['/bin/zsh', '-f', '/dev/fd/' + str(script_read)]
            script = script.replace(b'__EP_SCRIPT_FD__', str(script_read).encode())
        try:
            self.proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                start_new_session=True,
                pass_fds=() if script_read is None else (script_read,),
            )
        except BaseException:
            for fd in (script_read, script_write):
                if fd is not None:
                    os.close(fd)
            raise
        if script_read is not None:
            os.close(script_read)
        self.sel = None
        self.closed = False
        self.cleanup_verified = False
        self.seq = 0
        self.idle_bytes = 0
        self.timeout, self.cap, self.frame_cap = timeout, cap, frame_cap
        self.buf = bytearray()
        try:
            if (
                os.getpgid(self.proc.pid) != self.proc.pid
                or os.getsid(self.proc.pid) != self.proc.pid
            ):
                raise Refusal('owned_group_unverified')
            self.sel = selectors.DefaultSelector()
            for stream in (self.proc.stdout, self.proc.stderr):
                os.set_blocking(stream.fileno(), False)
                self.sel.register(stream, selectors.EVENT_READ)
            os.set_blocking(self.proc.stdin.fileno(), False)
            if script_write is not None:
                os.set_blocking(script_write, False)
                remaining = memoryview(script)
                deadline = time.monotonic() + timeout
                while remaining:
                    if time.monotonic() >= deadline:
                        raise Refusal('script_write_timeout')
                    try:
                        remaining = remaining[os.write(script_write, remaining) :]
                    except BlockingIOError:
                        time.sleep(0.005)
                os.close(script_write)
                script_write = None
        except BaseException:
            try:
                self.close()
            finally:
                if script_write is not None:
                    os.close(script_write)
            raise

    def _server_message(self, item, deadline):
        if 'method' not in item:
            return False
        if 'id' in item:
            rid = item['id']
            if not (
                type(rid) is int
                and 0 <= rid <= 2**53 - 1
                or type(rid) is str
                and 0 < len(rid) <= 128
            ):
                raise Refusal('server_request_id')
            response = {'jsonrpc': '2.0', 'id': rid}
            if item['method'] == 'ping':
                response['result'] = {}
            else:
                response['error'] = {'code': -32601, 'message': 'Unsupported server request'}
            self._send(response, deadline)
        return True

    def idle_tick(self):
        """Service existing stdio protocol only; never sends a browser/provider probe."""
        if self.closed:
            raise Refusal('client_closed')
        try:
            for key, _ in self.sel.select(0):
                try:
                    chunk = os.read(key.fileobj.fileno(), 8192)
                except BlockingIOError:
                    continue
                if not chunk:
                    self.sel.unregister(key.fileobj)
                    if key.fileobj is self.proc.stdout:
                        raise Refusal('transport_closed')
                    continue
                self.idle_bytes += len(chunk)
                if self.idle_bytes > self.cap:
                    raise Refusal('idle_output_cap')
                if key.fileobj is self.proc.stdout:
                    self.buf.extend(chunk)
            frames = 0
            while b'\n' in self.buf:
                frames += 1
                if frames > 64:
                    raise Refusal('idle_frame_cap')
                line, _, rest = self.buf.partition(b'\n')
                self.buf = bytearray(rest)
                if len(line) > self.frame_cap:
                    raise Refusal('frame_cap')
                try:
                    item = json.loads(
                        line, parse_constant=lambda _: (_ for _ in ()).throw(ValueError())
                    )
                except (ValueError, UnicodeDecodeError):
                    raise Refusal('invalid_frame') from None
                if type(item) is not dict or item.get('jsonrpc') != '2.0':
                    raise Refusal('invalid_protocol')
                if not self._server_message(item, time.monotonic() + self.timeout):
                    raise Refusal('unexpected_idle_response')
            if len(self.buf) > self.frame_cap:
                raise Refusal('frame_cap')
        except BaseException:
            self.close()
            raise

    def _send(self, value, deadline):
        data = memoryview(
            (json.dumps(value, separators=(',', ':'), allow_nan=False) + '\n').encode()
        )
        if len(data) > self.frame_cap:
            raise Refusal('request_cap')
        while data:
            if time.monotonic() >= deadline:
                raise Refusal('write_timeout')
            try:
                n = os.write(self.proc.stdin.fileno(), data)
                data = data[n:]
            except BlockingIOError:
                time.sleep(0.005)
            except (BrokenPipeError, OSError):
                raise Refusal('transport_closed') from None

    def notify(self, method, params=None):
        self._send(
            {'jsonrpc': '2.0', 'method': method, 'params': params or {}},
            time.monotonic() + self.timeout,
        )

    def call(self, method, params=None):
        try:
            return self._call(method, params)
        except BaseException:
            self.close()
            raise

    def _call(self, method, params=None):
        if self.closed:
            raise Refusal('client_closed')
        self.idle_bytes = 0
        self.seq += 1
        request_id = self.seq
        deadline = time.monotonic() + self.timeout
        self._send(
            {'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params or {}}, deadline
        )
        received = len(self.buf)
        while True:
            while b'\n' in self.buf:
                line, _, rest = self.buf.partition(b'\n')
                self.buf = bytearray(rest)
                if len(line) > self.frame_cap:
                    raise Refusal('frame_cap')
                try:
                    item = json.loads(
                        line, parse_constant=lambda _: (_ for _ in ()).throw(ValueError())
                    )
                except (ValueError, UnicodeDecodeError):
                    raise Refusal('invalid_frame') from None
                if type(item) is not dict or item.get('jsonrpc') != '2.0':
                    raise Refusal('invalid_protocol')
                if self._server_message(item, deadline):
                    continue
                if type(item.get('id')) is not int or item['id'] != request_id:
                    raise Refusal('response_identity')
                if 'error' in item or 'result' not in item:
                    raise Refusal('server_error')
                return item['result']
            if len(self.buf) > self.frame_cap:
                raise Refusal('frame_cap')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise Refusal('response_timeout')
            for key, _ in self.sel.select(remaining):
                try:
                    chunk = os.read(key.fileobj.fileno(), 8192)
                except BlockingIOError:
                    continue
                if not chunk:
                    self.sel.unregister(key.fileobj)
                    if key.fileobj is self.proc.stdout:
                        raise Refusal('transport_closed')
                    continue
                received += len(chunk)
                if received > self.cap:
                    raise Refusal('output_cap')
                if key.fileobj is self.proc.stdout:
                    self.buf.extend(chunk)
                # stderr is counted then discarded, never printed or persisted.

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            # SIGKILL before stdin EOF. Playwright MCP treats EOF and SIGTERM as a
            # graceful exit that closes its pages one by one through
            # chrome.tabs.remove, connector first; a kill mid-way left windows
            # with only part of their saved tabs. A hard kill only drops the
            # relay, so the extension ungroups the tabs intact for exact-ID
            # reconciliation. Do not poll/wait/reap the leader before the group
            # signal: its unreaped PID anchors this group ID against PID reuse.
            try:
                if (
                    os.getpgid(self.proc.pid) != self.proc.pid
                    or os.getsid(self.proc.pid) != self.proc.pid
                ):
                    raise Refusal('owned_group_unverified')
                os.killpg(self.proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                # No owned group remains; never target another group or enumerate.
                pass
            if self.proc.stdin:
                try:
                    self.proc.stdin.close()
                except OSError:
                    pass
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                raise Refusal('owned_child_unreaped') from None
            self.cleanup_verified = True
        finally:
            if self.sel is not None:
                self.sel.close()
            for stream in (self.proc.stdout, self.proc.stderr):
                if stream:
                    stream.close()
