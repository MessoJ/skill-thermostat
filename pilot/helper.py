"""Tiered AI helper. The tier is decided by the server (thermostat), never by the client or the model.

  full  : may give complete solutions
  hints : hints and explanations only, no complete solution
  nudge : one conceptual nudge or question, no code

The model is never given the reference solution or hidden tests. Prompts alone are not trusted to enforce
the tier, so every reply is also screened by `scrub` before the learner sees it.
"""
import os
import re

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


def _code_lines(block):
    return [l for l in block.splitlines() if l.strip() and not l.strip().startswith("```")]


def violates(tier, text, ref=None):
    """True if `text` gives away more than `tier` allows. `ref` is the reference solution (server-side only)."""
    if tier == "full":
        return False
    limit = 0 if tier == "nudge" else 3
    if any(len(_code_lines(b)) > limit for b in _FENCE.findall(text)):
        return True
    if ref:
        body = [l.strip() for l in ref.splitlines()[1:] if l.strip()]
        if body and sum(l in text for l in body) / len(body) >= 0.7:
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


class ClaudeHelper:
    """Claude via the Messages API. Needs `pip install anthropic` and ANTHROPIC_API_KEY. Not exercised live yet."""

    def __init__(self, model=None, api_key=None):
        import anthropic  # imported lazily so the pilot runs without the SDK
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = model or os.environ.get("HELPER_MODEL", "claude-sonnet-5-5")

    def reply(self, tier, task, message, code):
        user = (f"Exercise: {task['title']}\n{task['prompt']}\nFunction: {task['signature']}\n\n"
                f"Learner's current code:\n```python\n{code}\n```\n\nLearner's message: {message}")
        r = self.client.messages.create(model=self.model, max_tokens=600, system=SYSTEM[tier],
                                        messages=[{"role": "user", "content": user}])
        return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")


def make_helper(solutions=None):
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return ClaudeHelper()
        except ImportError:
            print("ANTHROPIC_API_KEY is set but the 'anthropic' package is missing; using the stub helper.")
    return StubHelper(solutions)
