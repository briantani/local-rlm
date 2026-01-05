import pytest
import threading
from src.core.budget import BudgetManager, BudgetExceededError

def test_budget_singleton():
    """Test that BudgetManager is a singleton."""
    b1 = BudgetManager()
    b2 = BudgetManager()
    assert b1 is b2
    b1.reset()

def test_budget_hard_stop():
    """Test 2.1: Hard Stop. Set budget to small amount, simulate calls, assert BudgetExceededError."""
    budget = BudgetManager()
    # Since it's a singleton, we must manually update the limit for this test
    budget.max_budget = 0.0001
    budget.reset()

    # Add some usage that is safe
    # $0.075 per 1M input -> 0.000000075 per token
    # 1000 tokens -> 0.000075
    budget.add_usage(1000, 0)
    budget.check_budget() # Should pass

    # Add enough usage to exceed $0.0001
    # 1000 more tokens -> total 2000 -> 0.00015 > 0.0001
    budget.add_usage(1000, 0)

    with pytest.raises(BudgetExceededError):
        budget.check_budget()

def test_budget_thread_safety():
    """Test 2.2: Thread Safety. Spawn 50 threads that all add costs simultaneously."""
    budget = BudgetManager()
    budget.reset()

    num_threads = 50
    tokens_per_thread = 1000

    def add_cost():
        budget.add_usage(tokens_per_thread, 0)

    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=add_cost)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Expected total input tokens: 50 * 1000 = 50,000
    assert budget.total_input_tokens == num_threads * tokens_per_thread

    # Expected cost: 50,000 * (0.075 / 1,000,000) = 0.00375
    expected_cost = (num_threads * tokens_per_thread / 1_000_000) * 0.075
    assert abs(budget.current_cost - expected_cost) < 1e-9
