"""Exercise facade lifecycle through real subprocess pipes, without a browser."""

import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import time
import unittest


SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "plugins/operating-doctrine/skills/browser-automation/scripts"
)


class FacadeLivenessTests(unittest.TestCase):
    def launch(self, idle=0.3):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        hook = Path(root.name) / "hook.py"
        hook.write_text("def decide(*args): return None\n")
        script = """
import json, sys, threading
sys.path.insert(0, sys.argv[1])
import browser_jobs as b
r=b.Route({'state_dir':sys.argv[2], 'headless_hook':sys.argv[3]})
def call(name, arguments):
    if name == 'start':
        with r.lock:
            r.open_control()
            r.jobs['fixture']={'status':'ready','client':None,'lock':threading.RLock()}
    elif name == 'finish':
        r.jobs['fixture']['status']='finished'
    return {}
r.call=call
# No real allocation occurs. Shutdown still closes its own control listener.
r.finish=lambda job: None
b.serve(r, idle_seconds=float(sys.argv[4]), poll_seconds=0.02)
"""
        proc = subprocess.Popen(
            [sys.executable, "-c", script, str(SCRIPTS), root.name, str(hook), str(idle)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.addCleanup(self.stop, proc)
        return proc, Path(root.name)

    @staticmethod
    def stop(proc):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream and not stream.closed:
                try:
                    stream.close()
                except BrokenPipeError:
                    # A child that already exited leaves buffered stdin unflushable.
                    pass

    def send(self, proc, method="ping", name=None):
        message = {"jsonrpc": "2.0", "id": 1, "method": method}
        if name:
            message["params"] = {"name": name, "arguments": {}}
        proc.stdin.write(json.dumps(message).encode() + b"\n")
        proc.stdin.flush()
        ready, _, _ = select.select([proc.stdout], [], [], 2)
        self.assertTrue(ready, "facade did not answer")
        self.assertIn("result", json.loads(proc.stdout.readline()))

    def test_stdio_eof_exits_without_waiting_for_idle_timeout(self):
        proc, root = self.launch(idle=30)
        self.send(proc, "initialize")
        proc.stdin.close()
        self.assertEqual(proc.wait(timeout=2), 0, proc.stderr.read())
        self.assertEqual(list(root.glob("*.sock")), [])

    def test_closed_response_pipe_exits_even_when_input_lingers(self):
        proc, root = self.launch(idle=30)
        self.send(proc, "initialize")
        proc.stdout.close()
        proc.stdin.write(b'{"jsonrpc":"2.0","id":2,"method":"ping"}\n')
        proc.stdin.flush()
        self.assertEqual(proc.wait(timeout=2), 0, proc.stderr.read())
        self.assertEqual(list(root.glob("*.sock")), [])

    def test_zero_job_lingering_tunnel_expires_and_binds_no_socket(self):
        proc, root = self.launch()
        self.send(proc, "initialize")
        self.assertEqual(list(root.glob("*.sock")), [])
        self.assertEqual(proc.wait(timeout=2), 0, proc.stderr.read())

    def test_partial_input_does_not_defeat_zero_job_timeout(self):
        proc, _ = self.launch()
        self.send(proc, "initialize")
        proc.stdin.write(b'{"jsonrpc":')
        proc.stdin.flush()
        self.assertEqual(proc.wait(timeout=2), 0, proc.stderr.read())

    def test_active_job_survives_timeout_and_finish_releases_socket(self):
        proc, root = self.launch()
        self.send(proc, "tools/call", "start")
        self.assertEqual(len(list(root.glob("*.sock"))), 1)
        # Wait longer than the zero-job deadline, while an actual job is held.
        with self.assertRaises(subprocess.TimeoutExpired):
            proc.wait(timeout=0.6)
        self.send(proc, "tools/call", "finish")
        self.assertEqual(proc.wait(timeout=2), 0, proc.stderr.read())
        self.assertEqual(list(root.glob("*.sock")), [])

    def test_ping_traffic_does_not_keep_zero_job_facade_alive(self):
        proc, _ = self.launch(idle=0.5)
        self.send(proc, "initialize")
        deadline = time.monotonic() + 2
        while proc.poll() is None and time.monotonic() < deadline:
            try:
                proc.stdin.write(b'{"jsonrpc":"2.0","id":2,"method":"ping"}\n')
                proc.stdin.flush()
                select.select([proc.stdout], [], [], 0.03)
                os.read(proc.stdout.fileno(), 4096)
            except BrokenPipeError:
                break
        self.assertEqual(proc.wait(timeout=1), 0, proc.stderr.read())


if __name__ == "__main__":
    unittest.main()
