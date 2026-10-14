"""Tiered AI helper. The tier is decided by the server (thermostat), never by the client or the model.

  full  : may give complete solutions
  hints : hints and explanations only, no complete solution
  nudge : one conceptual nudge or question, no code

The model is never given the reference solution or hidden tests. Prompts alone are not trusted to enforce
the tier, so every reply is also screened by `scrub` before the learner sees it.
"""
import ast
import json
import os
import re
import time
import urllib.error
import urllib.request

SYSTEM = {
    "full": "You are a coding assistant inside a learning app. Help the learner solve their Python exercise. "
            "You may write complete working code.",
    "hints": "You are a coding coach inside a learning app. Give hints and explain concepts or errors. "
             "Do NOT write a complete solution. At most 3 short lines of code, only to illustrate a general idea.",
    "nudge": "You are a coding coach inside a learning app. Reply with ONE short conceptual nudge or a single "
             "Socratic question, in at most two sentences. Write NO code.",
}
FALLBACK = ("I can't go further than that at this level. Try writing out your approach in words, then check "
            "it against the examples.")
_FENCE = re.compile(r"```.*?```", re.S)
_DEF_RE = re.compile(r"^\s*def\s+[a-zA-Z_]\w*\s*\(", re.M)


def _code_lines(block):
    return [l for l in block.splitlines() if l.strip() and not l.strip().startswith("```")]


def _ast_shape(code_str):
    """Canonicalize AST node types (ignoring variable names) to catch renamed solution leaks."""
    try:
        tree = ast.parse(code_str.strip())
    except SyntaxError:
        return None
    if isinstance(tree, ast.Module) and tree.body and isinstance(tree.body[0], ast.FunctionDef):
        stmts = tree.body[0].body
    else:
        stmts = tree.body
    if not stmts:
        return None
    return tuple(type(n).__name__ for s in stmts for n in ast.walk(s) if not isinstance(n, (ast.Load, ast.Store, ast.Name, ast.arg)))


def violates(tier, text, ref=None):
    """True if `text` gives away more than `tier` allows. `ref` is the reference solution (server-side only)."""
    if tier == "full":
        return False
    limit = 0 if tier == "nudge" else 3
    fences = _FENCE.findall(text)
    if any(len(_code_lines(b)) > limit for b in fences):
        return True
    if tier == "nudge" and _DEF_RE.search(text):
        return True
    if ref:
        fname = ref.splitlines()[0].split("(")[0].replace("def ", "").strip()
        if fname and re.search(rf"\bdef\s+{re.escape(fname)}\s*\(", text):
            return True
        body = [l.strip() for l in ref.splitlines()[1:] if l.strip()]
        if body and sum(l in text for l in body) / len(body) >= 0.7:
            return True
        ref_shape = _ast_shape(ref)
        if ref_shape and len(ref_shape) >= 4:
            for b in fences:
                inner = "\n".join(_code_lines(b))
                if _ast_shape(inner) == ref_shape:
                    return True
    return False


def scrub(tier, text, ref=None):
    return FALLBACK if violates(tier, text, ref) else text


class StubHelper:
    """Offline stand-in (no API key): canned replies per tier. `solutions` lets it show a solution at tier 'full'."""

    def __init__(self, solutions=None):
        self.solutions = solutions or {}

    def reply(self, tier, task, message, code):
        if tier == "full":
            sol = self.solutions.get(task["id"])
            return f"Here is one way to do it:\n```python\n{sol}```" if sol else "Here's a full walkthrough (stub)."
        if tier == "hints":
            return "Hint: work out what the function should return for the smallest possible input, then trace the first example by hand."
        return "What should happen for the smallest possible input?"


class GeminiHelper:
    """Gemini via Google Generative Language REST API. Needs GEMINI_API_KEY."""

    def __init__(self, model=None, api_key=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be set")
        self.model = model or os.environ.get("GEMINI_MODEL") or os.environ.get("HELPER_MODEL", "gemini-3.8-flash")

    def reply(self, tier, task, message, code):
        user = (f"Exercise: {task['title']}\n{task['prompt']}\nFunction: {task['signature']}\n\n"
                f"Learner's current code:\n```python\n{code}\n```\n\nLearner's message: {message}")
        payload = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM[tier]}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user}]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 600,
                "temperature": 0.7
            }
        }
        data = json.dumps(payload).encode("utf-8")
        models_to_try = [self.model]
        if self.model != "gemini-3-flash-preview":
            models_to_try.append("gemini-3-flash-preview")

        body = None
        last_err = None
        for current_model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={self.api_key}"
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            timeout = 8 if len(models_to_try) > 1 and current_model == models_to_try[0] else 30
            for attempt in range(2):
                try:
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        body = json.loads(resp.read().decode("utf-8"))
                        break
                except urllib.error.HTTPError as e:
                    err_body = e.read().decode("utf-8", errors="replace")
                    last_err = RuntimeError(f"Gemini API error ({e.code}) on {current_model}: {err_body}")
                    if e.code == 429 and attempt == 0:
                        wait = 5
                        try:
                            for d in json.loads(err_body).get("error", {}).get("details", []):
                                if "retryDelay" in d:
                                    wait = max(wait, float(d["retryDelay"].rstrip("s")))
                        except Exception:
                            pass
                        time.sleep(min(wait, 35))
                        continue
                    if e.code in (500, 503):
                        break  # Immediately fallback to secondary model
                except (TimeoutError, OSError) as e:
                    last_err = e
                    break
            if body:
                break

        if not body and last_err:
            raise last_err

        if not body:
            return ""
        candidates = body.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)


class ClaudeHelper:
    """Claude via the Messages API. Needs `pip install anthropic` and ANTHROPIC_API_KEY."""

    def __init__(self, model=None, api_key=None):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = model or os.environ.get("HELPER_MODEL", "claude-sonnet-4-5")

    def reply(self, tier, task, message, code):
        user = (f"Exercise: {task['title']}\n{task['prompt']}\nFunction: {task['signature']}\n\n"
                f"Learner's current code:\n```python\n{code}\n```\n\nLearner's message: {message}")
        r = self.client.messages.create(model=self.model, max_tokens=600, system=SYSTEM[tier],
                                        messages=[{"role": "user", "content": user}])
        return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")


def make_helper(solutions=None):
    if os.environ.get("GEMINI_API_KEY"):
        return GeminiHelper()
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return ClaudeHelper()
        except ImportError:
            print("ANTHROPIC_API_KEY is set but the 'anthropic' package is missing; using the stub helper.")
    return StubHelper(solutions)
