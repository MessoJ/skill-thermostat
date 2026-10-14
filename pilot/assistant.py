"""The AI helper. Its behaviour is set by the thermostat's assistance level, not by the learner.

StubAssistant is offline and uses each task's stored hint, approach and solution. ClaudeAssistant calls the
Anthropic Messages API and is selected automatically when ANTHROPIC_API_KEY is set. It has NOT been run
in the build environment (no API key there), so treat it as untested until you try it.
"""
import json
import os
import urllib.request

PROMPTS = {
    "hints": "Give ONE short hint that nudges the student. Do not write code and do not reveal the solution.",
    "guided": "Explain the approach in plain words or brief pseudocode, step by step. Do not give a complete "
              "working solution.",
    "full": "You may give a complete working solution with a short explanation.",
}


class StubAssistant:
    def reply(self, task, code, message, level):
        if level == "hints":
            return "Hint: " + task["hint"]
        if level == "guided":
            return "Approach: " + task["approach"]
        return "Here is a working solution:\n" + task["solution"]


class ClaudeAssistant:
    URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key, model="claude-sonnet-5-5", timeout=30):
        self.key, self.model, self.timeout = api_key, model, timeout
        self.fallback = StubAssistant()

    def reply(self, task, code, message, level):
        system = ("You are a coding tutor inside a practice tool. " + PROMPTS[level]
                  + " Keep the answer under 120 words unless giving a full solution.")
        user = (f"Task: {task['prompt']}\n\nStudent's current code:\n{code or '(empty)'}\n\n"
                f"Student's question: {message or '(none)'}")
        body = json.dumps({"model": self.model, "max_tokens": 600, "system": system,
                           "messages": [{"role": "user", "content": user}]}).encode()
        req = urllib.request.Request(self.URL, data=body, method="POST", headers={
            "content-type": "application/json", "x-api-key": self.key, "anthropic-version": "2023-06-01"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.load(r)
            return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
        except Exception as e:  # network, auth, quota...
            return self.fallback.reply(task, code, message, level) + f"\n(live helper unavailable: {type(e).__name__})"


def make_assistant():
    key = os.environ.get("ANTHROPIC_API_KEY")
    return ClaudeAssistant(key) if key else StubAssistant()
