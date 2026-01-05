import pytest
from src.core.budget import BudgetManager

@pytest.fixture(autouse=True)
def reset_budget():
    """
    Automatically reset the BudgetManager singleton before each test.
    This ensures that tests like 'test_budget_hard_stop' don't pollute
    the state for other tests.
    """
    budget = BudgetManager()
    budget.reset()
    budget.max_budget = 1.0  # Reset to default limit
    yield
    # Optional: Reset after test too
    budget.reset()
    budget.max_budget = 1.0
