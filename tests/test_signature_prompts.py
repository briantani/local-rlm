import dspy
from src.modules.coder import Coder


def test_coder_parses_expected_artifacts_comment():
    coder = Coder()
    code = """# Create data file
with open(f'{output_dir}/data.csv', 'w') as f:
    f.write('a,b\\n1,2\\n')
# EXPECTED_ARTIFACTS: data.csv
print('done')
"""
    # Monkeypatch the internal generator to return our code
    coder.generate_code = lambda task, context_summary: dspy.Prediction(python_code=code)

    pred = coder.forward(task='gen', context_summary='')
    assert hasattr(pred, 'expected_artifacts')
    assert 'data.csv' in pred.expected_artifacts
