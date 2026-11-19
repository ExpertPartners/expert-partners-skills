"""Protocol-v2 job glue kept separate from the supported 0.5 connector path."""

import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import uuid

from job_transport import Refusal
from relay_rpc import relay_rpc


ROOT = Path(__file__).resolve().parent
PAGES = (ROOT / "owned_pages_v2.js").read_text()


def generation_key(generation):
    return json.dumps(generation, separators=(",", ":"), sort_keys=True)


class RelayBroker:
    def __init__(self, root, settings, generation, job_id):
        self.socket = root / (f"r-{uuid.uuid4().hex[:10]}.sock")
        self.ledger = root / "relay-claims.sqlite3"
        self.proc = None
        try:
            bundle = Path(settings["bundle"])
            node = Path(settings["node"])
            if (
                not bundle.is_absolute()
                or not node.is_absolute()
                or hashlib.sha256(bundle.read_bytes()).hexdigest() != settings["bundle_sha256"]
            ):
                raise Refusal("relay_bundle_unverified")
            self.proc = subprocess.Popen(
                [
                    str(node),
                    str(ROOT / "relay_broker.cjs"),
                    str(self.socket),
                    str(bundle),
                    sys.executable,
                    str(self.ledger),
                    generation_key(generation),
                    job_id,
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            readable, _, _ = select.select([self.proc.stdout], [], [], 5)
            if not readable or self.proc.stdout.readline(16) != b"ready\n":
                raise Refusal("relay_broker_unavailable")
        except BaseException:
            self.stop()
            raise

    def rpc(self, method, **fields):
        if self.proc is None or self.proc.poll() is not None:
            raise Refusal("relay_broker_lost")
        try:
            return relay_rpc(self.socket, method, **fields)
        except (OSError, ValueError) as error:
            raise Refusal("relay_broker_operation_refused") from error

    def stop(self):
        if self.proc is not None:
            if self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=24)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(timeout=3)
            self.proc.stdout.close()
        self.socket.unlink(missing_ok=True)


def initialization_js(path):
    return (
        PAGES
        + f"""
const proc=Buffer.constructor("return process")();
const net=proc.getBuiltinModule("node:net");
const socketPath={json.dumps(str(path))};
const call=(method, fields={{}})=>new Promise((resolve,reject)=>{{
  const socket=net.createConnection(socketPath);
  let data="";
  socket.setEncoding("utf8");
  socket.setTimeout(22000,()=>socket.destroy(Error("relay_rpc_timeout")));
  socket.once("connect",()=>socket.write(JSON.stringify({{method,...fields}})+"\\n"));
  socket.on("data",chunk=>{{
    data+=chunk;
    if(data.length>262144)socket.destroy(Error("relay_rpc_response_too_large"));
  }});
  socket.once("error",()=>reject(Error("relay_rpc_failed")));
  socket.once("end",()=>{{
    try{{
      const value=JSON.parse(data);
      if(value.error||!("result" in value))throw Error("relay_rpc_refused");
      resolve(value.result);
    }}catch{{reject(Error("relay_rpc_refused"));}}
  }});
}});
if(page.context().pages().length!==1||page.url()!=="about:blank")
  throw Error("not_fresh_connector");
if(proc.__epBrowserJob)throw Error("already_attempted");
proc.__epBrowserJob=await newRelayOwnedState(page,{{
  marker:()=>proc.getBuiltinModule("node:crypto").randomBytes(16).toString("hex"),
  bindPage:(marker,initial)=>call("bindPage",{{marker,initial}}),
  observe:(tabId,url)=>call("observeTab",{{tabId,url}}),
  close:tabId=>call("close",{{tabId}}),
}});
return await proc.__epBrowserJob.snapshot();
"""
    )
