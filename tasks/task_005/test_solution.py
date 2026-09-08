import inspect

from solution import _apply_discount, rewards_total, store_credit_total


def test_store_credit_total_unchanged():
    assert store_credit_total(100, 10) == 97.2


def test_rewards_total_unchanged():
    assert rewards_total(100, 10) == 97.2


def test_shared_helper_is_imported():
    assert callable(_apply_discount)


def test_both_functions_delegate_to_helper():
    assert "_apply_discount(" in inspect.getsource(store_credit_total)
    assert "_apply_discount(" in inspect.getsource(rewards_total)