"""Prevent local credentials/configuration loading before test modules import."""
import os
import tempfile

os.environ["FRONTLINE_TEST_ISOLATION"] = "1"
_state = tempfile.TemporaryDirectory(prefix="tracex-test-client-")
for name in ("META_API_KEY", "MODEL_API_KEY", "OPENAI_API_KEY", "CLAUDE_API_KEY"):
    os.environ[name] = ""
for name, filename in (("META_BUDGET_PATH", "budget.sqlite"),
                       ("META_CAP_PATH", "calls.json"), ("META_RESOURCE_PATH", "host")):
    os.environ[name] = os.path.join(_state.name, filename)


def pytest_unconfigure(config):
    _state.cleanup()
