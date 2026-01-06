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
    BudgetManager._clear()
    budget = BudgetManager(max_budget=0.0001)

    # Register a test model with pricing
    budget.register_model("test-model", input_price_per_1m=0.075, output_price_per_1m=0.30)

    # Add some usage that is safe
    # $0.075 per 1M input -> 0.000000075 per token
    # 1000 tokens -> 0.000075
    budget.add_usage(input_tokens=1000, output_tokens=0, model_id="test-model")
    budget.check_budget()  # Should pass

    # Add enough usage to exceed $0.0001
    # 1000 more tokens -> total 2000 -> 0.00015 > 0.0001
    budget.add_usage(input_tokens=1000, output_tokens=0, model_id="test-model")

    with pytest.raises(BudgetExceededError):
        budget.check_budget()

def test_budget_thread_safety():
    """Test 2.2: Thread Safety. Spawn 50 threads that all add costs simultaneously."""
    BudgetManager._clear()
    budget = BudgetManager(max_budget=10.0)
    budget.register_model("test-model", input_price_per_1m=0.075, output_price_per_1m=0.30)

    num_threads = 50
    tokens_per_thread = 1000

    def add_cost():
        budget.add_usage(input_tokens=tokens_per_thread, output_tokens=0, model_id="test-model")

    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=add_cost)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Expected total input tokens: 50 * 1000 = 50,000
    model_stats = budget.get_model_stats("test-model")
    assert model_stats.total_input_tokens == num_threads * tokens_per_thread

    # Expected cost: 50,000 * (0.075 / 1,000,000) = 0.00375
    expected_cost = (num_threads * tokens_per_thread / 1_000_000) * 0.075
    assert abs(budget.current_cost - expected_cost) < 1e-9
