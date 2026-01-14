import shutil
from src.core.run_context import RunContext
from tests.conftest import MockREPL


class DynamicMockCoder:
    """Mock coder that creates the missing artifact on its second call via closure."""
    def __init__(self, run_context):
        self.call_count = 0
        self.run_context = run_context

    def __call__(self, task: str, context_summary: str = ""):
        self.call_count += 1
        # On first call, declare expected artifact but do not create it
        if self.call_count == 1:
            return type('Pred', (), {'python_code': "# attempt 1", 'expected_artifacts': ['fixme.png'], 'max_retries': 2})()
        # On second call, create the artifact file so agent can detect it
        (self.run_context.artifacts_dir / 'fixme.png').write_bytes(b'x')
        return type('Pred', (), {'python_code': "# attempt 2", 'expected_artifacts': ['fixme.png'], 'max_retries': 2})()


def test_intermediate_check_retries_and_registers(tmp_path):
    rc = RunContext(run_id='ic1', base_dir=tmp_path)
    mock_arch = type('Mock', (), {'__call__': lambda self, **kw: type('Pred', (), {'action': 'CODE'})()})()
    mock_repl = MockREPL(output='ok')
    mock_coder = DynamicMockCoder(rc)
    mock_responder = type('Mock', (), {'__call__': lambda self, **kw: type('Pred', (), {'response': 'Done'})()})()

    from src.core.agent import RLMAgent

    agent = RLMAgent(
        max_steps=3,
        architect=mock_arch,
        coder=mock_coder,
        repl=mock_repl,
        responder=mock_responder,
        run_context=rc,
    )

    agent.run('Make fixme.png')

    # coder should have been called at least twice (initial + retry)
    assert mock_coder.call_count >= 2
    # artifact should now be registered
    filenames = {a['filename'] for a in rc.artifacts}
    assert 'fixme.png' in filenames

    shutil.rmtree(rc.artifacts_dir)
