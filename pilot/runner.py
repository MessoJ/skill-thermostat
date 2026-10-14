"""Runs submitted code against an exercise's cases in a separate Python process."""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

try:
    import resource
except ImportError:
    resource = None

HARNESS = r'''
def _run_harness():
    import copy, io, json, os, signal, sys
    payload = json.loads(sys.stdin.read())
    out_fd = os.dup(1)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)
    os.close(devnull)
    sys.stdout = io.StringIO()

    def _emit(obj):
        data = json.dumps(obj).encode("utf-8")
        os.write(out_fd, data)
        os.close(out_fd)

    def _alarm(*_):
        raise TimeoutError("test timed out")

    has_alarm = hasattr(signal, "SIGALRM")
    if has_alarm:
        signal.signal(signal.SIGALRM, _alarm)
    code, fname, cases = payload["code"], payload["fname"], payload["cases"]
    del payload
    try:
        ns = {"__name__": "submission"}
        if has_alarm:
            signal.alarm(2)
        exec(compile(code, "<submission>", "exec"), ns)
        if has_alarm:
            signal.alarm(0)
        fn = ns.get(fname)
        if not callable(fn):
            raise NameError("function %s is not defined" % fname)
    except BaseException as e:
        if has_alarm:
            signal.alarm(0)
        _emit({"fatal": "%s: %s" % (type(e).__name__, e)})
        sys.exit(0)
    res = []
    for args in cases:
        try:
            if has_alarm:
                signal.alarm(2)
            got = json.loads(json.dumps(fn(*copy.deepcopy(args))))
            if has_alarm:
                signal.alarm(0)
            res.append({"got": got})
        except BaseException as e:
            if has_alarm:
                signal.alarm(0)
            res.append({"err": "%s: %s" % (type(e).__name__, e)})
    _emit({"results": res})

_run_harness()
'''


def _limits():
    if resource is None:
        return
    resource.setrlimit(resource.RLIMIT_CPU, (6, 6))
    resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 20, 1 << 20))
    if hasattr(resource, "RLIMIT_NOFILE"):
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    if hasattr(resource, "RLIMIT_NPROC"):
        try:
            resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
        except (ValueError, OSError):
            pass


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
                           text=True, timeout=timeout, preexec_fn=_limits if resource else None)
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
