"""One bounded call to a private browser relay broker over its Unix socket."""

import json
import socket


def relay_rpc(path, method, **fields):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(22)
        client.connect(str(path))
        client.sendall((json.dumps(dict(fields, method=method)) + "\n").encode())
        with client.makefile("rb") as data:
            raw = data.readline(262145)
        if len(raw) > 262144 or not raw.endswith(b"\n"):
            raise ValueError("relay_rpc_frame_invalid")
        reply = json.loads(raw)
        if not isinstance(reply, dict) or "result" not in reply or "error" in reply:
            raise ValueError("relay_rpc_refused")
        return reply["result"]
