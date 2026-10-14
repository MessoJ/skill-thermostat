"""Runs submitted code against an exercise's cases in a separate Python process.

Two backends:
  local   (default)  a child process with CPU/memory/file-size limits and a timeout. Survives honest mistakes (infinite loops, huge
                     allocations). NOT a security sandbox: the code runs as the app's user and can read what the app can read.
  remote  (set RUNNER_URL, optionally RUNNER_KEY)  POSTs the job to pilot.runner_service running in its own locked-down container
                     with no data, no secrets and no internet (see docker-compose.yml). Use this for anything reachable by others.
Only the standard library is imported here so the runner container needs nothing else.
"""
import json
import os
import resource
import subprocess
import sys
import urllib.error
import urllib.request

HARNESS = r'''
import json, signal, sys
payload = json.loads(sys.stdin.read())
real_out = sys.stdout
sys.stdout = open("/dev/null", "w")

def _alarm(*_):
    raise TimeoutError("test timed out")

signal.signal(signal.SIGALRM, _alarm)
try:
    ns = {"__name__": "submission"}
    signal.alarm(2)
    exec(compile(payload["code"], "<submission>", "exec"), ns)
    signal.alarm(0)
    fn = ns.get(payload["fname"])
    if not callable(fn):
        raise NameError("function %s is not defined" % payload["fname"])
except BaseException as e:
    real_out.write(json.dumps({"fatal": "%s: %s" % (type(e).__name__, e)}))
    sys.exit(0)
res = []
for args in payload["cases"]:
    try:
        signal.alarm(2)
        got = json.loads(json.dumps(fn(*args)))
        signal.alarm(0)
        res.append({"got": got})
    except BaseException as e:
        signal.alarm(0)
        res.append({"err": "%s: %s" % (type(e).__name__, e)})
real_out.write(json.dumps({"results": res}))
'''


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (6, 6))
    resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 20, 1 << 20))


def _fail(total, fatal):
    return dict(ok=False, passed=0, total=total, fatal=fatal, details=[])


def run_cases(code, fname, cases, expected, timeout=10):
    """Return dict(ok, passed, total, fatal, details=[{ok, got, err}]). `ok` means every case passed."""
    url = os.environ.get("RUNNER_URL")
    if url:
        return _remote(url, code, fname, cases, expected, timeout)
    return run_local(code, fname, cases, expected, timeout)


def _remote(url, code, fname, cases, expected, timeout):
    body = json.dumps(dict(code=code, fname=fname, cases=[list(c) for c in cases], expected=list(expected))).encode()
    headers = {"Content-Type": "application/json"}
    if os.environ.get("RUNNER_KEY"):
        headers["X-Runner-Key"] = os.environ["RUNNER_KEY"]
    try:
        with urllib.request.urlopen(urllib.request.Request(url.rstrip("/") + "/run", body, headers), timeout=timeout + 5) as r:
            out = json.loads(r.read())
        if not isinstance(out, dict) or "ok" not in out:
            raise ValueError("bad runner reply")
        return out
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as e:
        return _fail(len(cases), "The code runner is unavailable (%s)" % type(e).__name__)


def run_local(code, fname, cases, expected, timeout=10):
    payload = json.dumps({"code": code, "fname": fname, "cases": [list(c) for c in cases]})
    try:
        p = subprocess.run([sys.executable, "-I", "-c", HARNESS], input=payload, capture_output=True,
                           text=True, timeout=timeout, preexec_fn=_limits)
    except subprocess.TimeoutExpired:
        return _fail(len(cases), "Timed out (infinite loop?)")
    try:
        out = json.loads(p.stdout)
    except ValueError:
        if p.returncode < 0:
            return _fail(len(cases), "Stopped: the code used too much time or memory")
        return _fail(len(cases), "Crashed before reporting (%s)" % ((p.stderr or "no output")[-200:].strip()))
    if "fatal" in out:
        return _fail(len(cases), out["fatal"])
    details = [dict(ok=("got" in r and r["got"] == exp), got=r.get("got"), err=r.get("err"))
               for r, exp in zip(out["results"], expected)]
    passed = sum(d["ok"] for d in details)
    return dict(ok=passed == len(cases), passed=passed, total=len(cases), fatal=None, details=details)
