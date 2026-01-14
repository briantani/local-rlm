import dspy
import json
import re
import pytest

from src.core.budget import BudgetManager, BudgetWrapper
from src.modules.coder import Coder
from src.modules.architect import Architect
from src.modules.responder import Responder


class ScriptedMockLM(dspy.LM):
    """A scripted MockLM that returns different dspy.Prediction objects
    based on simple pattern matching of the prompt. Useful to emulate
    complex model behavior without network calls.
    """
    def __init__(self, name: str = "scripted-mock"):
        super().__init__(model=name)

    def __call__(self, *args, **kwargs):
        # dspy adapters often call LM with `messages=[{'role':'user','content':...}]`
        prompt = None
        if args:
            prompt = args[0]
        elif "messages" in kwargs:
            msgs = kwargs.get("messages")
            if isinstance(msgs, (list, tuple)) and msgs:
                # join content fields
                prompt = "\n".join(str(m.get("content", "")) for m in msgs)
        prompt = str(prompt or "").lower()
        text = prompt

        # Architect decision patterns
        if any(k in text for k in ["what is", "decide", "should i code", "action:"]):
            if re.search(r"\d+\s*\*\s*\d+", text) or "calculate" in text:
                return ['{"reasoning": "Detected math prompt", "action": "CODE"}']
            return ['{"reasoning": "Short answer", "action": "ANSWER"}']

        # Coder: return code and optionally expected_artifacts
        if "generate csv" in text or "write csv" in text or "save to" in text:
            code = "# EXPECTED_ARTIFACTS: results.csv\nwith open('results.csv','w') as f:\n    f.write('a,b\\n1,2')\nprint('saved')"
            # Return a JSON string matching the Coder signature
            return ['{"reasoning": "Generated CSV writer", "python_code": ' + json.dumps(code) + ', "expected_artifacts": ["results.csv"]}']

        if "fibonacci" in text:
            code = "def fib(n):\n    a,b=0,1\n    for _ in range(n):\n        a,b=b,a+b\n    print(a)\n\nfib(10)"
            return ['{"reasoning": "Fibonacci code", "python_code": ' + json.dumps(code) + ', "expected_artifacts": []}']

        # Responder: include artifacts_info in response for verification
        if "finalize" in text or "render final" in text:
            # Try to extract any artifacts info present in the prompt text.
            m = re.search(r"([\w\-\.]+\.csv[^\n]*)", prompt, re.IGNORECASE)
            artifacts_info = m.group(1) if m else ""
            return ['{"reasoning": "Assembling final report", "response": "Final report including: ' + str(artifacts_info).replace('"', '\\"') + '"}']

        # Default fallback
        return ['{"reasoning": "fallback", "response": "MOCK_DEFAULT"}']


def setup_scripted_lm():
    bm = BudgetManager(max_budget=10.0)
    lm = ScriptedMockLM()
    wrapper = BudgetWrapper(lm, bm)
    wrapper._model_id = "scripted-mock"
    dspy.settings.configure(lm=wrapper)
    return wrapper


def test_architect_returns_code_with_scripted_lm():
    setup_scripted_lm()
    arch = Architect()
    pred = arch.forward(query="What is 1234 * 5678?", data_desc="")
    assert hasattr(pred, "action")
    assert pred.action in ("CODE", "ANSWER")


def test_coder_returns_expected_artifacts_and_code():
    setup_scripted_lm()
    coder = Coder()
    task = "Generate CSV file: save to results.csv"
    pred = coder.forward(task=task, context_summary="")
    assert hasattr(pred, "python_code")
    assert "EXPECTED_ARTIFACTS" in pred.python_code or getattr(pred, "expected_artifacts", None)
    # If expected_artifacts present, verify it's a list containing results.csv
    if getattr(pred, "expected_artifacts", None):
        assert "results.csv" in pred.expected_artifacts


def test_responder_includes_artifacts_info():
    setup_scripted_lm()
    responder = Responder()
    resp = responder.forward(query="Render final answer", context="", artifacts_info="results.csv: summary section")
    # Responder.forward should return a Prediction with response text including the artifacts_info
    assert hasattr(resp, "response")
    assert "results.csv" in resp.response
