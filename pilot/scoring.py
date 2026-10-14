"""Auto-scoring: run submitted code against a task's tests in a resource-limited subprocess.

NOT a hardened sandbox (no network or filesystem isolation). Fine for a supervised local pilot;
before exposing this to the internet, run it inside a container or a proper sandbox.
"""
import json
import subprocess
import sys

HARNESS = r'''
import contextlib, io, json, sys
data = json.loads(sys.stdin.read())
ns, passed, err = {}, 0, ""
def emit(obj):
    sys.__stdout__.write("\n@@RESULT@@" + json.dumps(obj) + "\n")
try:
    with contextlib.redirect_stdout(io.StringIO()):
        exec(data["code"], ns)
    fn = ns[data["fn"]]
except BaseException as e:
    emit({"passed": 0, "total": len(data["tests"]), "error": "could not load: " + repr(e)[:160]})
    sys.exit(0)
for args, expected in data["tests"]:
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            got = fn(*json.loads(json.dumps(args)))
        if json.loads(json.dumps(got)) == expected:
            passed += 1
        elif not err:
            err = "wrong answer for input " + json.dumps(args)[:80]
    except BaseException as e:
        if not err:
            err = repr(e)[:160]
emit({"passed": passed, "total": len(data["tests"]), "error": err})
'''


def _limits():  # runs in the child before exec (Linux/macOS)
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 2**20, 512 * 2**20))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2**20, 2**20))


def run_tests(code, task, timeout=5.0):
    """Return dict(passed, total, ok, error). ok means every test passed."""
    total = len(task["tests"])
    if len(code) > 20000:
        return dict(passed=0, total=total, ok=False, error="submission too long")
    payload = json.dumps(dict(code=code, fn=task["fn"], tests=task["tests"]))
    try:
        p = subprocess.run([sys.executable, "-I", "-c", HARNESS], input=payload, capture_output=True,
                           text=True, timeout=timeout, preexec_fn=_limits)
    except subprocess.TimeoutExpired:
        return dict(passed=0, total=total, ok=False, error="timed out")
    line = next((ln for ln in reversed(p.stdout.splitlines()) if ln.startswith("@@RESULT@@")), None)
    if line is None:
        return dict(passed=0, total=total, ok=False, error="crashed or exceeded limits")
    r = json.loads(line[len("@@RESULT@@"):])
    return dict(passed=r["passed"], total=r["total"], ok=r["passed"] == r["total"], error=r["error"])
